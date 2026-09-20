# `Cannot read properties of undefined (reading 'map')` in `renderInvoiceLines`

## 1. Read what the stack already rules out

The message is "reading `'map'` **of undefined**", not "reading `'lines'` of undefined" and not
"of null". That is a real narrowing, so use it before guessing:

- The **container object exists**. If the invoice object itself were missing you would see
  `Cannot read properties of undefined (reading 'lines')`. So a fetch happened and returned
  *something*; that something does not carry the array field.
- The field is **`undefined`, not `null`**. A database NULL or an explicit `null` in JSON would
  usually surface as `null`. `undefined` means the key was **absent** from the object, or a getter
  that used to produce it is gone.

So the shape of the bug is: *an object arrived at the component with a missing key, and nothing
between the data source and line 88 checked.* TypeScript did not catch it, which means there is an
`as Invoice`, a `!`, or an untyped `res.json()` (returns `any`) somewhere on that path. The type is
asserting a contract the runtime is not honoring.

## 2. One measurement splits the hypothesis space in half

Before touching code, go into the error tracker and **group the events by invoice id** (or by URL
if the id is in the path). You are asking one question: are the 3% a *set of invoices* or a
*random sample of traffic*?

- **A small set of ids, each hitting repeatedly, reproducible on every load** → data-shape bug.
  Some invoices genuinely lack lines in the new query path. Go to section 3A.
- **Ids spread widely, the same id sometimes fine and sometimes broken** → non-deterministic
  bug: a partial or failed upstream response, or a cache serving a bad payload. Go to 3B.
- **Ids spread widely but clustered by navigation path or route** → the two-code-paths case, 3C.

Also pull from the same events: route/URL, whether it was a soft client navigation or a hard load
(referrer helps), region/deployment, tenant, and time distribution (steady 3% vs spiky). Spiky and
load-correlated is strong evidence for 3B. Steady is evidence for 3A or 3C.

## 3. Ranked hypotheses, each with a cheap test

### 3A. The normalization layer got deleted along with the API route (most likely)

The old client-side fetch almost certainly went through an API route or a hook that shaped the
response: `lines: rows ?? []`, a zod parse with `.default([])`, a mapper function, or a
`select`/`include` that always attached the relation. Moving the fetch into the server component
typically means querying the source directly and skipping that shaping. Invoices whose line set is
empty, or whose type never has lines, now arrive with the key absent instead of with `[]`.

Test, two minutes, no production access needed:

1. `git log --since="2026-09-08" --oneline -- "**/invoice*"` and find the move commit.
2. `git show <sha>` and read the **deleted** side of the diff. Compare the old response shaping to
   the new query. Look specifically for a lost `?? []`, a lost zod `.default`, a lost `include` /
   `select` on the relation, or a lost mapper.
3. Then find an invoice that should hit it and load its page locally:
   - an invoice with zero line rows,
   - a draft, void, or credit-note invoice,
   - the oldest invoice in the table, and one created before the last schema migration.

If any of those reproduces, you are done, and 3% is simply the share of that category in traffic.

### 3B. The fetch can fail or return an error body, and nothing checks it

Two common shapes, both of which produce exactly "an object with the wrong keys":

- `const invoice = await res.json()` with **no `res.ok` check**. On a 429, 500, or 503 the upstream
  returns a JSON error envelope with a 4xx/5xx status, `res.json()` parses it happily, and you are
  now rendering `{ error: "...", requestId: "..." }` as an invoice. Load-correlated, a few percent,
  never reproducible locally.
- An aggregate fetch using `Promise.allSettled` (or a try/catch that returns a partial object) where
  one leg failing leaves the lines slot unset.

Also in this family: the server-side request now runs from a different network position than the
browser did. Different timeouts, different auth, a header the browser sent that the server does
not, and an upstream that occasionally rate-limits the server's single origin IP.

Test: grep the new server component path for `res.json()` without an adjacent `res.ok` / status
check, and for `allSettled`. `if (!res.ok) throw new Error(...)` turns a silent 3% render crash into
a loud, attributable fetch error, which is the outcome you want even before you know the cause.

### 3C. Two call sites, or two data paths into the same component

`InvoiceTable` is at line 41 of its own file, so it is rendered from somewhere else. Check whether
**every** call site now gets lines from the new server component:

```
rg -n "InvoiceTable" --glob "!node_modules"
```

Watch for a print/PDF route, a modal or drawer, an email preview, an embedded summary tab, or a
storybook-ish dev route that was never migrated and still passes a lighter object. Traffic share of
one secondary route is a very natural 3%.

The App Router variant of this, worth testing explicitly because dev never shows it: **soft
navigation vs hard load**. If a list page prefetches or passes down a list-shaped invoice (no
lines) and the detail page only fetches the full object on a cold load, then users who click through
from the list break while users who paste the URL do not. Test in a production build (`npm run
build; npm run start`), navigate from the list into a detail page rather than loading the URL
directly, and try it with a warm router cache.

### 3D. Cache serving a payload from before the change

If the new server component uses cached `fetch`, `unstable_cache`, `cache()`, ISR, or a CDN, then a
payload captured during the deploy window, or an error response that got cached, can be served to a
fraction of requests indefinitely while everything else looks correct. Fits "3%" and "started last
Thursday" well.

Test: check whether the failing events correlate with cache hits (response headers,
`x-vercel-cache` or your equivalent), and whether purging the relevant cache tag makes the rate drop
to zero. A rate that falls to zero on purge and then creeps back up points at an error response
being cached, which is 3B plus caching.

### 3E. Serialization across the server/client boundary

Server component to client component props go through the RSC payload. Plain arrays and objects
survive; **getters, class instances, lazy ORM relation proxies, Maps, and Sets do not**. If the ORM
returned a model whose `lines` was a getter or a lazily hydrated relation, the client sees a plain
object with that key gone. This is usually 100% rather than 3%, so rank it low unless only one of
several fetch paths returns a model instance and the others return plain rows. It is still worth one
check: log `Object.keys(invoice)` on the server and in the client component and diff them. If the
server has the key and the client does not, it is serialization and nothing else.

## 4. Manufacture the repro from production, at the boundary

You do not need to guess your way to a repro. Add one narrow, temporary probe **where the data
enters**, not where it crashes:

```ts
// in the server component, immediately after the fetch/query
if (!Array.isArray(invoice?.lines)) {
  console.error("invoice_lines_missing", {
    invoiceId: invoice?.id ?? "unknown",
    status: res?.status,           // if there is a fetch
    keys: Object.keys(invoice ?? {}),
    cache: res?.headers?.get("x-vercel-cache") ?? null,
    route: /* pathname */,
    nav: "server",
  });
}
```

`Object.keys` is the payload that does the work: it tells you instantly whether you are looking at
an error envelope (`["error","requestId"]`), a list-shaped invoice (`["id","total","status"]`), or a
full invoice with one key missing (`["id","customer","totals"]` and no `lines`). Log keys and ids,
never the invoice body, so you are not writing customer data into logs.

Ship that, wait for a handful of events, then fetch the named invoice locally. That is your
reproduction, and it arrives within hours rather than by inspiration.

## 5. Stop the bleeding without destroying the signal

Do both of these, and understand that the first one is not the fix:

1. **Guard the render** so 3% of loads stop throwing:

```tsx
const lines = Array.isArray(invoice.lines) ? invoice.lines : [];
```

   Then render a real empty state, not a blank table. An invoice showing zero lines is wrong for
   most of these cases, so pair the guard with the probe from section 4 or you have converted a
   visible crash into a silent wrong number, which is worse. A crash on an invoice page is bad; a
   silently incorrect invoice total is bad *and* invisible.

2. **Add an `error.tsx`** at the invoice route segment so a render throw degrades that segment
   instead of blanking the page, and so the error carries a digest you can match to logs.

## 6. The durable fix

Wherever the invoice enters the process, parse it instead of asserting it:

```ts
const Invoice = z.object({
  id: z.string(),
  lines: z.array(InvoiceLine),   // required on purpose, no silent default
  // ...
});

if (!res.ok) throw new Error(`invoice fetch ${res.status}`);
const invoice = Invoice.parse(await res.json());
```

That moves the failure from line 88 of a render function to the boundary, names the field and the
invoice, and makes the 3% attributable the first time it happens. If empty line sets are genuinely
valid, encode that as `.default([])` **at the boundary** where it is a stated product decision, not
as `?? []` in the component where it is an accident.

Two follow-ups worth the time: delete the `as Invoice` / `!` that let this compile, and if the old
API route did shaping that the new path skipped, check whether any other field went the same way.
A deleted normalization layer rarely loses exactly one key.

## 7. What would convince me it is fixed

- A failing invoice id from the logs that I can load locally and watch break, then load again after
  the change and watch render correctly.
- An explanation of why it is 3% and not 100% and not 0.1%, expressed as a population: "invoices
  with no line rows are 2.8% of views", or "the print route is 3% of invoice traffic", or "the
  upstream 429s about 3% of the time at peak". If I cannot name the population, I have patched a
  symptom and the real bug is still there behind the guard.
- The error rate at zero for a full traffic cycle including a peak, since a load-correlated cause
  can hide for hours.
- A test that fails without the fix: render `InvoiceTable` with an invoice that has no lines, and
  assert the boundary parse rejects an error envelope.

## 8. One caution about the timeline

"Started last Thursday, around when we moved the fetch" is a strong lead and not proof. Check
whether anything else shipped in that window: a migration, an upstream service version, a rename
(`lines` to `lineItems`) that a stale cache or an unmigrated call site still uses. Confirm the
correlation by finding the first event timestamp in the tracker and comparing it against the deploy
time for that commit specifically. If the first error predates the move, the move only exposed
something older, and fixing the server component will not close it.
