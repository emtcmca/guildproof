# API review: `POST /api/users/:id/refund`

I assumed an Express-style handler. No middleware, types or DB schema were provided, so nothing outside these three lines counts as protection.

## Contract

- **Method and path:** `POST /api/users/:id/refund`
- **Inputs:** `:id` from the URL, and `amount` from the JSON body. Nothing else is read: no auth context, no reason, no idempotency key, no charge id.
- **Side effect:** `stripe.refund({ charge: chargeFor(id), amount })`. This is irreversible money movement.
- **Output:** always `200 {"ok": true}` when the `await` resolves. Nothing else is returned.
- **Failure behavior:** undefined. There is no try/catch.

## Findings (worst-first)

1. ❌ **No authorization on a money-moving endpoint, and IDOR by construction.**
   - **What's wrong:** No visible authN or role check. The target charge is derived from `req.params.id` alone.
   - **Why it bites:** Any caller who reaches this route can refund any user's charge by changing the id. If customers can reach it, they can refund themselves. Refunds should be staff-only.
   - **Fix:** Require authentication. Require a refund-capable role (support or admin). Check that the target charge belongs to the caller's tenant. Refuse with 403, or 404 to avoid confirming that the resource exists.

2. ❌ **A missing `amount` refunds everything.**
   - **What's wrong:** `amount` is destructured and passed through unvalidated.
   - **Why it bites:** As I read Stripe's refund API, omitting `amount` refunds the whole remaining charge. So `{}` or a typo'd key becomes a full refund. Strings, floats, negatives, `NaN`, and dollars-vs-cents mix-ups all reach Stripe as-is. If `req.body` is undefined, the destructure throws a TypeError, which is a 500.
   - **Fix:** Validate at the boundary. Require a positive integer in minor units, cap it at the locally tracked refundable balance, and reject with 400 or 422. Never let an absent amount mean "all". If you want full refunds, make them an explicit `full: true` path.

3. ❌ **Not idempotent.**
   - **What's wrong:** No idempotency key and no dedupe record.
   - **Why it bites:** Double-clicks, client retries, gateway timeouts and load-balancer replays each issue another refund. Partial refunds stack up to the full charge. Stripe's over-refund cap stops you exceeding the charge, but it does not stop repeated refunds within it.
   - **Fix:** Require a client-supplied `Idempotency-Key` header. Pass it to Stripe as the request idempotency key. Also insert a local refund row with a UNIQUE constraint on that key before calling Stripe.

4. ❌ **Refund is addressed by user, not by charge, and `chargeFor` is unreviewed.**
   - **What's wrong:** `chargeFor(req.params.id)` picks the charge implicitly, and its result is neither awaited nor null-checked.
   - **Why it bites:**
     - A user with several charges gets whichever one the function returns, possibly the wrong one.
     - An unknown user yields `undefined`, so Stripe errors and you get an unhandled 500.
     - If `chargeFor` is async, a Promise is passed as `charge`.
   - **Fix:** Address the resource that is actually refunded, e.g. `POST /api/charges/:chargeId/refunds`. Look up the charge by id, verify ownership, and 404 if it is missing.

5. ❌ **No error handling.**
   - **What's wrong:** No try/catch around the `await`.
   - **Why it bites:** Stripe errors (already refunded, insufficient balance, invalid charge, network failure) either become unhandled rejections or fall to whatever the default handler does. Under Express 4 an async throw can hang the request. A default handler can also echo Stripe's raw error message to the client. That leaks internals and is the wrong status code (500 instead of 409 or 422).
   - **Fix:** Catch Stripe errors by type and map them: 4xx for caller-fixable problems, 502 or 503 for upstream failures. Return a stable machine-readable error shape with no raw upstream text.

6. ❌ **No local record and no partial-failure story.**
   - **What's wrong:** The Stripe call is the only effect. There is no refund row, no ledger or balance update, and no audit entry.
   - **Why it bites:** If Stripe succeeds and the response is lost or a later write fails, your system has refunded money it has no record of. A retry then refunds again (see finding 3). Disputes can't be reconstructed.
   - **Fix:** Write a `pending` refund row first, with actor, charge, amount, reason and idempotency key. Call Stripe. Then mark the row `succeeded` or `failed`. Reconcile through Stripe's refund webhooks.

7. ⚠️ **`200 {ok:true}` is a dishonest response.**
   - **What's wrong:** The response says nothing about the refund's outcome.
   - **Why it bites:** As I understand it, refunds can be pending or fail asynchronously, so "ok" may be false a minute later. The caller gets no refund id to reconcile against.
   - **Fix:** Return `201` (or `202` if pending) with `{ refundId, status, amount, currency }`.

8. ⚠️ **No abuse controls.**
   - **What's wrong:** No rate limit, no per-refund or daily ceiling, no approval step.
   - **Why it bites:** A compromised or malicious staff token can drain revenue at API speed.
   - **Fix:** Add rate limiting and a velocity cap per actor. Add a second-approver threshold above an amount you choose.

9. ⚠️ **No observability.**
   - **What's wrong:** No visible logging or audit trail.
   - **Why it bites:** At 3am you can't tell who refunded what.
   - **Fix:** Emit a structured audit event with actor, charge id, amount, reason, idempotency key and result. Don't log card data or secrets.

10. ⚠️ **No `reason` input.**
    - **What's wrong:** The endpoint does not capture why a refund was issued.
    - **Why it bites:** Finance and dispute review have no context, and the audit trail from finding 9 has nothing to say about intent.
    - **Fix:** Add a required `reason` (an enum plus optional note) and store it on the refund row.

11. ✅ **Over-refund of a single charge is capped by Stripe.**
    - Per Stripe's refund API, total refunds on a charge can't exceed the charge amount. That limits the worst case for one charge only. It does not fix findings 1 to 3.

## Highest-severity issue

The endpoint has no visible authorization, and the refund target comes straight from the URL param. Any caller who can reach it can refund any user's charge.

## Confirm-these

Treat each as absent until shown.

- **Auth middleware:** confirm it runs on this route and that a role check gates refunds.
- **Tenant scoping:** confirm `chargeFor` enforces it, and confirm what it returns for no charge, several charges, and an async result.
- **`stripe.refund(...)`:** I don't recognize that as a method on the official Stripe Node SDK, which uses `stripe.refunds.create`. Confirm it's a wrapper, and confirm the wrapper forwards an idempotency key and passes `amount` through unchanged.
- **Body parsing and CSRF:** confirm a JSON body parser is mounted. If auth is cookie-based, confirm CSRF protection exists.
- **Error handling:** confirm the framework version and global error handler, and that they don't echo upstream error text.
- **Downstream state:** confirm whether any webhook or job updates your DB, invoice or entitlement state after a refund.
- **Rate limiting:** confirm rate limiting exists upstream of this route.