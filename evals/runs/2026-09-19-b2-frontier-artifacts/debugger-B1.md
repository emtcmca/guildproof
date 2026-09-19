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
