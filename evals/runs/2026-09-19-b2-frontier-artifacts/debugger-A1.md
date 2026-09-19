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
