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
