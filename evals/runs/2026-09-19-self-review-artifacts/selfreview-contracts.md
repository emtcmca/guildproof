# Self-review experiment: contracts (fixed before any build output was seen, 2026-09-19)

## T1: invoice endpoint
GET /api/invoices/:id returns one invoice that belongs to the caller's organization, as an
InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }.
- An invoice in another organization, or one that doesn't exist, returns the same 404.
- Nothing else about the invoice or the customer leaves the server (no email, tax_id,
  payment_token, portal_password_hash, org_id, customer_id).
- Malformed ids never produce a 500.

## T2: withRetry for the payments client
- Retries only failures that can succeed on retry: network errors (ECONNRESET, ETIMEDOUT and
  similar), 429, and 5xx. Never other 4xx.
- Never retries a non-idempotent call (createCharge, refund) unless the caller supplies an
  idempotency key that is sent unchanged on every attempt. Reads (getCharge) may retry freely.
- Exponential backoff with jitter. Honors Retry-After on 429/503.
- Bounded by a total time budget, not only an attempt count.
- After the last attempt, the original error reaches the caller unchanged (status, code intact).

## T3: public dashboard share links
- Only the dashboard's owner, in the dashboard's organization, can create a link. Anyone else
  gets 404.
- Tokens are unguessable (at least 128 bits from a CSPRNG) and stored only as a hash.
- Links expire (30 days or less by default) and can be revoked. Expired, revoked and unknown
  tokens all return the same 404.
- GET /share/:token returns only the dashboard's title and config: nothing about the owner, the
  organization, or other dashboards.
- The public route is read-only.
