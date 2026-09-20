# B2 inputs: one user message per specialist per input, sent to both arms verbatim

Written 2026-09-19, before any B2 run. Where an input reuses a code artifact from the self-review
run, that artifact already has a blind judge's defect list on file, so the ground truth predates B2.

Artifacts referenced below live in `../runs/2026-09-19-self-review-artifacts/`.

## debugger

**D-1** — the README's own example:
> TypeError: Cannot read properties of undefined (reading 'map') at renderInvoiceLines
> (invoice-table.tsx:88) at InvoiceTable (invoice-table.tsx:41). It hits about 3% of invoice page
> loads. I think it started last Thursday, around when we moved the invoice fetch into a server
> component. I don't have a reproduction.

**D-2**
> `checkout.spec.ts` fails about 1 run in 10 on CI and never locally. It started after we upgraded CI
> from Node 20 to 22 last week. The failure is `expect(received).toBe(expected) — Expected: "paid",
> Received: "pending"` in "marks the order paid after the webhook". Can you fix it?

## security-review

**S-1** — "Review this before we merge." + `sr-t3-haiku.md` (share links: plaintext tokens, no
expiry, owner name in the public response, no org check).

**S-2** — "Security pass on this, please." + `sr-t1-haiku.md` (invoice endpoint: org-scoped, but
leaks email and tax_id; malformed ids return 500).

## api-reviewer

**A-1**
> Review this API before we publish it to partners:
> - `POST /v1/orders` creates an order. Returns 200 with `{ "error": "..." }` in the body on
>   validation failure.
> - `PATCH /v1/orders/{id}` takes the full order object and replaces it.
> - `GET /v1/orders?page=N` returns 50 orders per page, newest first.
> - `POST /v1/orders/{id}/refund` refunds the order. Calling it twice refunds twice.
> - Auth: an API key in the `?key=` query parameter.

**A-2** — "Review the API this helper wraps and how it's called." + `sr-t2-haiku.md` (retry wrapper
with no idempotency handling).

## verifier

**V-1** — the case-41 handler and contract (`fixtures/invoice-handler-planted-leak.md`).

**V-2** — "Verify this against its contract." + `contract-t1.txt` + `sr-t1-frontier.md`. It is
well built, but leaks `customer_id`. The subtle one.
