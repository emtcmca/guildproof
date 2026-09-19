=== OUTPUT W ===

# `Cannot read properties of undefined (reading 'map')` in `renderInvoiceLines`

## Failure

**Expected:** every invoice page load renders the line-item table.

**Actual:** on a reported ~3% of loads, rendering throws `TypeError: Cannot read properties of undefined (reading 'map')` inside `renderInvoiceLines` (`invoice-table.tsx:88`), called from `InvoiceTable` (`invoice-table.tsx:41`).

**Trigger condition:** unknown. That is the actual open question, and it is the thing to establish before anything else.

Two things the trace tells us that are worth stating explicitly, because they constrain the search:

1. **The frames are client-component frames.** `InvoiceTable` is rendering and calling a local helper. So whatever is `undefined` reached this component as a prop (or as a field of a prop) that crossed the server/client boundary, or was derived locally from one. The fetch moving server-side does not remove the boundary, it moves it.
2. **The stack is two frames deep with no intermediate `.map` frame.** So the `undefined` value is either an argument passed into `renderInvoiceLines` from line 41, or a closure variable it reads. Do not assume it is `invoice.lines`. It could equally be a nested field (`group.items`, `line.taxes`, `invoice.lines[i].allocations`). Which one it is changes the ranking below significantly.

**Attribution note:** "started last Thursday" and "around when we moved the invoice fetch into a server component" are your reports, not verified facts. The correlation is plausible and I am ranking on it, but Probe 0 below exists specifically to test it, because if the fingerprint predates the change, most of this list collapses.

## Reproduction

None supplied, so the first job is to manufacture one. A 3% intermittent failure is almost always deterministic on some hidden input. The reproduction is: *find the input*.

Two facts are needed before a repro can be written, and both are cheap:

- **The actual text of `invoice-table.tsx` lines 30-95.** Which expression is `.map`, and what prop path feeds it. Zero cost, and without it the ranking below is partly guesswork about which object is `undefined`.
- **The diff of Thursday's change**, specifically: what the old client-side fetch returned versus what the server component now passes. `git log --since="10 days ago" -p -- <fetch path> invoice-table.tsx`.

Given those two, the repro is: reproduce the payload shape, not the click. Either render `InvoiceTable` with the suspected prop shape in a unit test, or replay a captured failing payload.

## Probe 0 (run before ranking anything)

**Was the error present before Thursday?** Query the error tracker for this fingerprint with the date filter removed, going back 60 days.

- Zero occurrences before the deploy: the change is implicated, proceed with the ranking below.
- Nonzero: the deploy changed the *rate*, not the *existence*, and hypotheses D and E rise sharply while A and B fall.

This costs one search and can invalidate half of what follows. It goes first.

## Probe 1 (the bisect that splits the whole space)

**Group the error events by invoice ID / route param, then by release version and session start time.** Every error tracker does this. The distribution answers the single most discriminating question available:

| Observation | Reads as | Ranking effect |
|---|---|---|
| Concentrated on a small set of invoice IDs, recurring | **Data-shape** cause: some invoices have a shape the component cannot render | A, B rise; D, F fall |
| Spread thinly across many distinct invoice IDs, roughly uniform | **Request-time** cause: cache, deploy skew, or a failing fetch path | D, E, F rise; A, B fall |
| Clustered in windows immediately after deploys, then decaying | **Deploy/cache skew** | F rises to top |
| Concentrated in one tenant/org/locale | Tenant-specific data or a per-tenant feature flag branch | A rises, and the branch becomes the search target |

3% is a number that fits either story, which is exactly why it cannot be reasoned from directly. Concentrated-versus-spread is the cut.

## Hypotheses

Ranked by likelihood × cost to test. Confidence is stated as my own, not as established.

### A. The server fetch selects a different shape than the old client fetch, and one branch omits the relation (confidence: moderate-high, ~35%)

**Cause:** the previous client-side fetch hit an endpoint whose serializer always emitted `lines: []`. The server component now queries the source directly, and at least one call path does not request the relation (a missing Prisma `include`/`select`, a different GraphQL selection set, a second call site that builds a partial invoice object for a summary view and reuses the same component). Absent relation arrives as `undefined`, not `[]`.

**Why plausible:** this is the single most common way a client-to-server-component move changes a payload shape. It also explains a *stable minority* percentage cleanly if the partial path is one route among several, or one status branch among several.

**Cheapest probe:** grep for every construction site of the prop `InvoiceTable` receives and compare their selection sets against each other. One call site lacking the relation that the others have is the answer, visible in source without running anything. Distinguishes A from B because B requires the *same* query to return `undefined` for some rows, whereas A predicts a difference between *call sites*.

### B. Same query, row-dependent nullability: a legitimate invoice state has no lines (confidence: moderate, ~25%)

**Cause:** the query is correct everywhere, but for some rows the relation resolves to `null`/`undefined` rather than `[]`. Candidates: zero-line invoices (drafts, voided, fully-credited, `$0` recurring placeholders), credit notes stored in a sibling table, legacy rows migrated without lines, or a left join that yields `null` and a mapper that does not normalize it.

**Why plausible:** fits a small stable percentage better than almost anything else, because "share of invoices in an unusual state" is naturally a few percent. The old client path may have coerced the null to `[]` in a transform layer that the server path bypasses.

**Cheapest probe:** one read-only query. `SELECT status, COUNT(*) FROM invoices i WHERE NOT EXISTS (SELECT 1 FROM invoice_lines l WHERE l.invoice_id = i.id) GROUP BY status;` Then compare that count as a share of *recently viewed* invoices against 3%. A match near 3% is strong corroboration. A result of zero rows kills B outright, which is why this probe is worth running even though A outranks it.

### C. The `undefined` is a nested field, not the top-level collection (confidence: moderate, ~20%)

**Cause:** `invoice.lines` is present and non-empty, but a per-line collection is absent on some lines. `line.taxes`, `line.allocations`, `line.discounts`, `group.items`. `renderInvoiceLines` maps the outer array successfully and throws on the inner one for a specific line.

**Why plausible:** the two-frame stack is consistent with this if the inner `.map` is inline on line 88 rather than in its own named function. And a per-line optional relation naturally produces a low, stable error rate. I rank this below A and B only because I have not seen line 88 yet. **Reading line 88 promotes or eliminates this in seconds, which makes it the cheapest hypothesis on the list to resolve.**

**Cheapest probe:** read `invoice-table.tsx:80-95` and name the exact expression. If the `.map` on 88 is on a nested path, C moves to the top and A/B need re-scoping to that relation.

### D. The server component swallows a fetch failure and returns a partial object (confidence: low-moderate, ~10%)

**Cause:** the new server-side fetch is wrapped in `try/catch` (or a `.catch(() => ({}))`, or a result type whose error branch returns a default) so a timeout or upstream 5xx yields `{}` or `{ invoice: {} }` instead of throwing. The page then renders with `lines` absent. The *reported* failure is the render crash, but the *real* failure is a silent upstream error.

**Why plausible:** 3% is a very ordinary failure rate for a dependency under load, and this is the hypothesis that best explains a *uniform spread across invoice IDs*. It is also the one where fixing the render would hide a real availability problem, so it must not be eliminated by assumption.

**Cheapest probe:** compare the error-event timestamps against upstream latency/error-rate graphs for the same window. Correlation of the render errors with upstream p99 spikes or non-2xx rate confirms; flat upstream metrics under a spiky render error rate kills it. No code change required. This is the probe that distinguishes "bad data" from "failed fetch", which A/B/C cannot do.

### E. Serialization across the RSC boundary drops or mangles the field (confidence: low, ~7%)

**Cause:** the value is a non-plain type that does not survive the server-to-client prop boundary intact, or passes through a `JSON.parse(JSON.stringify(...))` normalization step that drops `undefined`-valued and function-valued keys, or a lazy ORM proxy/getter whose property is not enumerated when serialized. Present on the server, absent on the client.

**Why plausible:** it is a genuinely boundary-specific failure mode, which fits the timing. Ranked low because the common presentation is a loud "Only plain objects can be passed to Client Components" error rather than a silent `undefined`, and no such error was reported.

**Cheapest probe:** log `typeof lines` and `Array.isArray(lines)` at two points, immediately before the server component passes the prop, and at the top of the client component, keyed by invoice ID. Present on the server and absent on the client is unambiguous and confirms E while simultaneously eliminating A, B, and D. Costs one deploy of two log lines.

### F. Deploy or cache skew: an old RSC payload or old client bundle (confidence: low, ~3%)

**Cause:** either a cached RSC payload written by the pre-Thursday code is being served to the new client component, or clients holding a stale JS chunk from before the deploy are receiving the new payload. Also fits a route cached with `revalidate` where some entries were populated by the older shape.

**Why plausible:** explains low-percentage, time-clustered, self-healing errors, and explains a start date exactly. Ranked last because it usually decays toward zero within hours or a day of the deploy, and you describe a rate that has persisted for several days.

**Cheapest probe:** group errors by release/build ID and by time-since-deploy (both standard error-tracker dimensions). Errors confined to one build ID, or decaying after each deploy, confirms. Errors on the current build at a steady rate kills it.

## Most likely, and why

**Lead theory: A, with B as the close second, and the two share a mechanism.**

The mechanism, stated concretely so it can be falsified: the old client-side fetch passed through a layer that guaranteed `lines` was an array (an API serializer defaulting to `[]`, or a client-side mapper normalizing null). Moving the fetch into a server component removed that layer from the path. The component's prop type still *declares* an array, and TypeScript still believes it at compile time, but nothing now enforces it at runtime, so a subset of invoices arrive with the field absent and `renderInvoiceLines` throws on the first `.map`.

**What that explains:** the timing (the guarantee left the path on Thursday), the stable low rate (a fixed minority of invoices or one minority call path), the `undefined` rather than `null` (an omitted relation, not a null column), the absence of a server-side error (the server is fine, the shape is merely thinner), and the lack of a repro (the engineer testing it opened normal invoices).

**What it does not explain, and I am not going to paper over it:** nothing in the evidence rules out D. A uniform 3% is *also* exactly the signature of a flaky upstream behind a swallowed error, and in that case the render crash is a symptom two layers downstream of the real defect. A and D are separated cleanly by Probe 1 (concentrated versus spread) plus the upstream-metric correlation in D's probe, so this ambiguity is resolvable and costs nothing to resolve.

**What would prove me wrong:**

- Probe 0 finds the fingerprint before Thursday: the deploy is a red herring and the rate change needs its own explanation.
- Probe 1 shows errors spread uniformly across hundreds of distinct invoice IDs: A and B are both wrong, D and F take over.
- Line 88 turns out to map a nested per-line collection: the search target changes from the invoice query to that relation, and C leads.
- Every construction site of the prop has an identical selection set and the zero-line query returns no rows: A and B are both dead and E becomes the lead despite its low prior.

## Two cautions before anyone touches code

**Do not add `lines?.map` or `(lines ?? []).map` yet.** It will make the error stop, and it will be indistinguishable from a fix. If the cause is D, that change converts a visible upstream outage into an invoice page that silently renders zero line items on a real invoice, which is materially worse than a crash. If the cause is B, an empty table may be correct, but that is a product decision to make knowingly rather than a null-guard to sprinkle.

**Separate the trigger from the root cause.** The trigger is whichever invoice or request condition Probe 1 identifies. The root cause is that a typed boundary is not validated at runtime: the prop's declared type stopped matching reality the moment the guaranteeing layer left the path, and nothing failed loudly at the boundary. Fixing only the trigger leaves the next shape change to be discovered the same way, in production, at 3%.

## Ordered next steps

1. **Probe 0** (error tracker, no date filter). Does the failure predate the deploy?
2. **Read `invoice-table.tsx:30-95`.** Name the exact `undefined` path. Resolves C immediately.
3. **Probe 1** (group errors by invoice ID, release, time-since-deploy). Splits data-shape from request-time.
4. Then run whichever of A's grep, B's count query, or D's metric correlation the step-3 result points at.

Send me the text of lines 30-95 and the group-by-invoice-ID result and I can collapse this to one or two hypotheses rather than six.


=== OUTPUT X ===

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


=== OUTPUT Y ===

# Undefined array in `renderInvoiceLines`

## Failure

**Expected:** every invoice page load renders the line-item table.
**Actual:** in roughly 3% of loads, `renderInvoiceLines` reads `.map` off `undefined` and the render throws at `invoice-table.tsx:88`.

**Trigger condition: not yet known.** That is the central open question, and almost everything below is arranged to answer it. What the trace does tell us:

- The array is missing **during render**, not in an event handler or effect. `renderInvoiceLines` is called from `InvoiceTable` (line 41), so the bad value is in scope at the moment the component body runs. This rules out a later state update or a user interaction as the trigger.
- The two frames given contain no React internals and no frames above `InvoiceTable`. I am treating that as a truncated trace rather than evidence, because I do not know how your reporter formats these. If the untruncated trace is available it will tell us whether the throw happens on the server during RSC render or in the browser after hydration, and those are different bugs.
- 3% is a *rate*, and a rate is compatible with two very different shapes: a fixed minority of invoices that always fail, or any invoice failing occasionally. Those shapes point at opposite causes.

**Two of your statements are unverified and I am not treating either as established:**

1. "Started last Thursday." This is recollection. Your error tracker has a first-seen timestamp; compare it to the deploy time before anything else. If the error predates the server-component move, hypotheses 1 through 4 all lose most of their weight and the rewrite is a coincidence.
2. "Around when we moved the invoice fetch into a server component." Temporal proximity to a deploy is suggestive and no more. It is common for a deploy to *expose* a data condition that existed for months.

## Reproduction

You do not have one, and the fastest way to get one is also the single most valuable probe in this whole document, so do it first.

**Step 1: pull the failing identifiers.** From the error tracker, extract the invoice id (or route URL) for every occurrence, plus user/tenant and timestamp. If the reporter is not capturing the route params, add that now; without it you are debugging blind and every step below gets more expensive.

**Step 2: the bisect that splits the hypothesis space.** Request those exact invoice routes directly, several times each.

- **A specific invoice fails every time** → the failure is **deterministic and data-shaped**. Go to hypotheses 1 and 2. You now have a permanent reproduction and can stop guessing.
- **The same invoice fails sometimes and succeeds sometimes** → the failure is **non-deterministic**, a timing or infrastructure condition. Go to hypotheses 3 and 4.
- **Nothing fails** → the condition depends on session, tenant, or the client build, which is itself evidence pointing at hypothesis 4.

That one observation eliminates roughly half the list, which is why it is step one rather than a hypothesis of its own.

**What I need from the source to go further**, and cannot infer:

- The ~15 lines around `invoice-table.tsx:88`, so I know *which* array is undefined (`invoice.lines`? `data.items`? a grouped intermediate?).
- The props type of `InvoiceTable` and whether the field is declared optional.
- Whether `invoice-table.tsx` carries `'use client'`, and the server component that now renders it.
- The diff of the fetch move. Specifically: what shaped the payload before, and what shapes it now.

## Hypotheses

Ranked by likelihood times cost-to-test. Confidence is my own and is low across the board until the bisect runs, because the evidence available so far cannot distinguish a data bug from a timing bug.

---

### 1. The old fetch path applied a default that the server component does not

**Confidence: moderate, and highest of the set.**

**Cause.** The previous client fetch went through something that normalized the payload: an API route, a response schema, a mapper, a hand-written `lines: rows ?? []`. The server component now reads the database or upstream service and passes rows into props more or less raw. Invoices whose line relation is absent (never populated, a join dropped in the rewrite, a genuinely zero-line invoice represented as `null` rather than `[]`) now arrive as `undefined` where they previously arrived as `[]`.

**Why plausible.** It explains a stable small percentage without any randomness: 3% is simply the share of invoices in that state. It explains onset at the deploy. It explains why no one can reproduce it, because the engineer reproducing picks a normal invoice. It is also the single most common way this class of rewrite breaks, since the defaulting logic tends to live in the layer that was removed.

**Cheapest probe.** Read the deleted code, not the new code. In the diff for the fetch move, search the removed lines for `??`, `|| []`, `.map(`, a zod/valibot schema, or any DTO mapper, and check whether an array default was among the casualties. Then query the database directly for the failing ids from step 1 and look at the line relation: absent, `null`, or empty array. Ten minutes, no deploy, and it either produces the defect or clears the hypothesis outright.

**Confirms if:** the failing ids share a property (status `draft`, `void`, migrated legacy records, one tenant) and the removed layer contained the default. **Killed if:** the failing ids are ordinary invoices with normal line rows in the database.

---

### 2. The field does not survive the server-to-client serialization boundary

**Confidence: moderate.**

**Cause.** Props crossing from a server component into a client component must be serializable. A key whose value is `undefined` is dropped. A class instance, a getter, a `Map`/`Set`, an ORM lazy-relation proxy, or a `Decimal` does not arrive as the shape the type claims. If the line array is exposed as a getter on a model instance, or is a lazy relation that is materialized only when touched, the client receives an object with no such key at all.

**Why plausible.** It explains onset precisely, because this boundary did not exist before the rewrite. It is the failure mode unique to the change you named, which is exactly why it deserves a slot even though hypothesis 1 outranks it.

**Why it is ranked second rather than first.** On its own it predicts a ~100% failure rate, not 3%. It only fits if the value is non-plain for *some* rows, which makes it a variant of hypothesis 1 more than a separate bug. I am keeping it separate because the fix differs: hypothesis 1 wants a default, hypothesis 2 wants an explicit plain-object mapping at the boundary.

**Cheapest probe.** In the server component, immediately before returning, log `invoiceId`, `typeof lines`, `Array.isArray(lines)`, and `Object.getPrototypeOf(invoice)?.constructor?.name`. Then log `Object.keys(props)` at the top of `InvoiceTable`. Compare the two for the same request. If the server sees an array and the client sees no key, the boundary ate it, and that is unambiguous.

**Confirms if:** the field is present server-side and missing client-side for the same request. **Killed if:** the field is already `undefined` before it is handed across, which redirects you to hypothesis 1 or 3.

---

### 3. A failed or partial upstream fetch is being swallowed into a success-shaped object

**Confidence: low to moderate. This is the leading candidate if the bisect shows non-determinism.**

**Cause.** The new server component fetch sits inside a `try`/`catch`, a `Promise.allSettled`, a `Promise.all` over several queries, or a path with a timeout. On failure it returns a partial object rather than throwing, so the render proceeds with a shape that is missing the lines. The component then treats an error as data.

**Why plausible.** 3% is a very ordinary upstream error-plus-timeout rate. It explains why a specific invoice cannot be reproduced on demand. Crucially it also explains why the *rate* is stable while the *identity* of the failures is not, which hypothesis 1 cannot do.

**Cheapest probe.** Join by request id. For each client-side TypeError, find the server log line for the same request and check for a paired 5xx, timeout, or caught exception in the same window. No code change needed if request ids already flow into both logs.

**Confirms if:** essentially every occurrence has a paired upstream failure. **Killed if:** the server log for those requests is clean, meaning the data arrived fine and something after the fetch lost it.

---

### 4. Deployment skew: a stale client bundle or cached RSC payload meeting new code

**Confidence: low, but very cheap to test and it explains the 3% shape unusually well.**

**Cause.** During and after a deploy, browsers hold an older JS bundle, and RSC payloads can be cached or replayed against a client build that expects different props. A client component compiled before the rewrite, receiving the new payload (or the reverse), reads a key that moved or was renamed.

**Why plausible.** Skew errors characteristically hit a small single-digit percentage and *decay* after each deploy, then spike at the next one. If your error graph has that sawtooth shape, this is close to diagnostic on its own.

**Cheapest probe.** Plot occurrences per hour against deploy times, and check whether the build/deployment id on failing sessions differs from current. If your reporter does not attach a build id, add it, since it is a one-line change that pays for itself permanently.

**Confirms if:** occurrences cluster immediately after deploys and decay. **Killed if:** the rate is flat across days with no deploys, which is the likelier outcome given you describe a steady 3%.

---

### 5. Something unrelated to the rewrite, surfaced by coincidence

**Confidence: low, and it is here to stay honest rather than because I favor it.**

**Cause.** A data migration, a new invoice type, an upstream API version change, or a bot/crawler hitting the route with unusual params, all landing in the same week as the deploy.

**Cheapest probe.** The first-seen timestamp in the tracker, compared against the deploy timestamp. If the first occurrence precedes the deploy by even a few hours, this hypothesis jumps to the top of the list and the other four largely collapse. This is the cheapest observation in the document and it is the reason I put "verify the date" ahead of everything else.

## Most likely, and why

**Lead theory: hypothesis 1.** The removed fetch layer was also the layer that guaranteed an array, and a small stable slice of invoices has no lines in the underlying data.

**What it explains.** All four pieces of evidence you gave. The stable low percentage (a fixed minority of records, not a race). The onset at the deploy (the guarantee was in the deleted code). The absence of a reproduction (any invoice an engineer picks by hand is a normal one). The synchronous render-time frame (the value is already wrong when it is handed to the component, not corrupted later).

**Where it is weak, and what would prove me wrong.** It cannot explain a deterministic *per-id* failure turning out to be non-deterministic. If a single invoice id fails only sometimes, hypothesis 1 is dead on the spot and hypothesis 3 takes the lead. It also does not explain the shape of the trace if the throw turns out to be server-side only, or client-side only, in a way that implicates the boundary. I am ranking it first on the strength of the pattern, not on evidence that distinguishes it from hypothesis 3, and I want to be explicit that the bisect in step 2, not this ranking, is what should decide.

## Trigger versus root cause

Whichever of the five is the proximate trigger, there is a separate defect underneath, and it is worth naming now so the eventual fix does not stop at the symptom.

`renderInvoiceLines` calls `.map` on a value it never verified, and TypeScript did not object. That means the type in force at line 88 claims the field is a present array when the runtime value is optional. The usual reasons: an `as` cast, a hand-written interface that drifted from the actual payload, a `any` from the fetch, or a server boundary where the declared prop type was never checked against what is actually serialized.

Adding `?? []` at line 88 would make this stack trace stop appearing in roughly 3% of loads. It would also render an invoice with silently zero line items, which for a billing surface is a worse outcome than a crash, and it would leave the type lie in place to break somewhere else later. Identify which hypothesis is true first, fix the data or the boundary, and separately close the gap between the declared type and the real payload so the compiler can catch the next instance.


=== OUTPUT Z ===

# `Cannot read properties of undefined (reading 'map')` in `renderInvoiceLines`

## What the stack trace actually establishes

Only this: at line 88, the thing you called `.map` on was `undefined`, not an empty array. That distinction is the whole case. An empty relation gives you `[]` and `[].map` works fine. So the field you are reading is **absent or null**, which means this is a data-shape problem, not a data-volume problem. Stop thinking about "invoices with no lines" and start thinking about "invoices whose `lines` key never arrived."

Two things worth confirming before you trust the rest of your framing:

1. **Verify the Thursday correlation.** Pull the first-seen timestamp of this error group from your error tracker and compare it against the deploy time of the server-component change. If the first event predates the deploy, the server component is a coincidence and the real cause is upstream. This costs two minutes and it is the cheapest way to avoid spending a day down the wrong hole.
2. **Group the 3% by invoice ID.** If a handful of IDs account for most events, it is bad rows or a bad query path. If the IDs are spread evenly across many invoices and many users, it is timing, caching, or deploy skew. These two shapes lead to completely different fixes, and the grouping tells you which one you have before you form a theory.

## Why the server-component move is a good lead

Moving a fetch from the client into a server component changes three things at once, and any of the three produces exactly this failure at a low rate.

**It deletes the guard you used to have.** The client version almost certainly had `if (isLoading) return <Skeleton/>` or `if (!data) return null` in front of the render. That early return was load-bearing: it meant the component never rendered without data. Now the server component renders unconditionally with whatever the query returned, including a partial result. Run `git log -p --since="2 weeks ago" -- invoice-table.tsx` and the adjacent server component, and look specifically for a deleted conditional. That is the single most likely regression in this change.

**It added a serialization boundary.** Props crossing from a server component into a client component go through the RSC payload, which only carries plain, serializable values. If your data layer hands back an ORM model, a class instance, a `Map`, a getter, or a lazily-hydrated relation, the plain-object projection can silently drop it. Nothing throws at the boundary; the field just is not there on the other side. This is the mechanism that best explains "no reproduction locally," because locally you probably hit the path where the relation is already hydrated.

**It put the fetch behind a cache.** Server-side fetches land in the framework data cache, and rendered output can land in a page cache or on a CDN. A cached entry written against the old response shape, or a prerendered payload served to a newer client bundle, gives you a small, stubborn percentage of failures that survive redeploys and never reproduce in dev. If a field got renamed anywhere in this change (`lineItems` to `lines`, or a GraphQL alias), cache hits from before the rename are a textbook 3%.

## Ranked hypotheses, each with the test that kills it

| # | Hypothesis | Distinguishing evidence |
|---|---|---|
| 1 | Partial result renders because the loading/empty guard was removed with the client fetch | The deleted conditional shows up in the diff; `Object.keys(invoice)` at the throw site is missing `lines` entirely |
| 2 | A second query path does not select the relation (one call site includes it, another does not) | Failing invoice IDs all arrive via one route, filter, or pagination branch; diff the two queries |
| 3 | Non-plain value dropped crossing the server/client boundary | The server sees a valid `lines` before returning, the client sees it absent. This is the bisect described below |
| 4 | Partial GraphQL/REST success: `errors` present, `data.invoice.lines === null` | `lines` is present with value `null`, not absent. Check whether the server code ignores a partial-error response |
| 5 | Stale cache entry or version skew between cached payload and client bundle | Errors cluster by cache key or region and decay after a purge; the invoice renders fine on hard reload |
| 6 | A legacy or special-case row class (imported invoices, drafts, credit notes, voided) | Failing IDs share a `status` or `type` value |

Note that 3% being *stable* rather than spiking argues against a pure deploy-skew race and toward hypotheses 1 through 4.

## How to get the reproduction you do not have

You will not find this by reading code, because the code looks correct on the path you can run. Instrument the throw site and let production tell you which hypothesis is true. The goal is one deploy that returns a verdict, not a guess.

At the failure point in `invoice-table.tsx`:

```tsx
function renderInvoiceLines(invoice: Invoice) {
  if (!Array.isArray(invoice?.lines)) {
    captureMessage("invoice.lines not an array at render", {
      level: "error",
      extra: {
        invoiceId: invoice?.id ?? "(no id on object)",
        invoiceKeys: invoice ? Object.keys(invoice) : null,
        linesType: typeof invoice?.lines,
        linesIsNull: invoice?.lines === null,
        status: invoice?.status,
        type: invoice?.type,
        source: invoice?.__source, // stamped by the server component, see below
      },
    });
    return <InvoiceLinesUnavailable invoiceId={invoice?.id} />;
  }
  // existing render
}
```

`Object.keys(invoice)` is the highest-value field in that payload. It splits the hypothesis space three ways in a single measurement:

- `lines` **absent from the key list** points at the serialization boundary or a query that never selected it (hypotheses 2, 3, 5).
- `lines` **present with value `null`** points at the resolver or a partial-error response (hypothesis 4).
- `lines` **present as an object rather than an array** means a `Map` or keyed collection reached the client (hypothesis 3, confirmed).

Then bisect the boundary itself. In the server component, immediately before returning the props:

```tsx
if (!Array.isArray(invoice.lines)) {
  logger.error("lines missing BEFORE serialization", {
    invoiceId: invoice.id,
    keys: Object.keys(invoice),
  });
}
// tag the path so the client log can attribute it
return <InvoiceTable invoice={{ ...invoice, __source: "invoice-page-server" }} />;
```

If the server log fires, the data was already wrong and the problem is the query or the cache. If only the client log fires, the data was correct and the boundary ate it. One deploy, and you know which half of the system to fix. Keep the `__source` tag if more than one server component renders this table, because hypothesis 2 lives or dies on knowing which call site produced the bad props.

## The fix, in two layers

**Layer one, today: make the failure visible instead of fatal.** Ship the guard above. But do not write `invoice.lines ?? []` and call it done. On an invoice, silently rendering zero lines is worse than crashing: the customer sees a $0 invoice, believes it, and you have turned a loud frontend error into a quiet billing error that nobody reports. The guard must render an explicit "line items unavailable" state and keep reporting to your error tracker. A crash you can see beats a wrong number you cannot.

**Layer two, after the telemetry lands: fix the cause and make the type honest.** Whatever the instrumentation says, there is almost certainly a lying type behind this. TypeScript let line 88 compile, which means `lines` is declared non-optional somewhere it can be missing in practice. Look for the place that asserts it: an `as Invoice` cast, a generated type that marks a nullable column non-null, a `JSON.parse` returning `any`, or an interface hand-written to describe the happy path. Change the boundary type to `lines?: Line[] | null`, let the compiler point at every unguarded read, and parse the payload at the edge (zod or an equivalent) so a shape violation fails once at a named boundary with a useful message instead of at an arbitrary `.map` three components deep.

## One prediction to check first

If I had to pick one thing to look at before the instrumentation ships: diff the removed client fetch against the new server component and find the early return that disappeared. Regressions from a fetch relocation are far more often a deleted guard than an exotic serialization edge case, and that check costs one `git diff` rather than a deploy cycle.

