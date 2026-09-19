```ts
// with-retry.ts
type ClientError = {
  status?: number;
  code?: string;
  headers?: Headers | Record<string, unknown>;
};

export interface RetryOptions {
  /**
   * true only if repeating the call cannot double-apply it:
   * reads, or writes that send the SAME idempotency key on every attempt.
   * Required on purpose, so every call site has to decide.
   */
  idempotent: boolean;
  retries?: number;     // extra attempts after the first (default 3)
  baseDelayMs?: number; // backoff base (default 200)
  maxDelayMs?: number;  // backoff cap; a longer Retry-After gives up instead of waiting (default 5000)
  onRetry?: (err: unknown, attempt: number, delayMs: number) => void;
}

// The server never did any work, so these are safe to retry for any call.
const NOT_PROCESSED_CODES = new Set(['ECONNREFUSED', 'EAI_AGAIN']);

// The request may or may not have been processed. Only safe to retry when the call is idempotent.
const AMBIGUOUS_CODES = new Set(['ECONNRESET', 'ETIMEDOUT', 'EPIPE', 'ECONNABORTED', 'UND_ERR_SOCKET']);
const AMBIGUOUS_STATUSES = new Set([500, 502, 503, 504]);

function isRetryable(err: unknown, idempotent: boolean): boolean {
  const { status, code } = (err ?? {}) as ClientError;
  if (status === 429) return true; // rate limited: rejected before processing
  if (code && NOT_PROCESSED_CODES.has(code)) return true;
  if (!idempotent) return false;
  return (
    (status !== undefined && AMBIGUOUS_STATUSES.has(status)) ||
    (code !== undefined && AMBIGUOUS_CODES.has(code))
  );
}

// Reads Retry-After as either seconds ("2") or an HTTP date.
function retryAfterMs(err: unknown): number | undefined {
  const h = (err as ClientError)?.headers;
  if (!h) return undefined;
  const raw =
    typeof (h as Headers).get === 'function'
      ? (h as Headers).get('retry-after')
      : (h as Record<string, unknown>)['retry-after'] ?? (h as Record<string, unknown>)['Retry-After'];
  const value = String((Array.isArray(raw) ? raw[0] : raw) ?? '').trim();
  if (!value) return undefined;
  const secs = Number(value);
  if (Number.isFinite(secs)) return Math.max(0, secs * 1000);
  const at = Date.parse(value);
  return Number.isNaN(at) ? undefined : Math.max(0, at - Date.now());
}

export async function withRetry<T>(fn: () => Promise<T>, opts: RetryOptions): Promise<T> {
  const { idempotent, retries = 3, baseDelayMs = 200, maxDelayMs = 5000, onRetry } = opts;

  for (let attempt = 0; ; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (attempt >= retries || !isRetryable(err, idempotent)) throw err;

      const hinted = retryAfterMs(err);
      // A user is waiting on this request. If the server asks for a long pause, fail now rather than hang.
      if (hinted !== undefined && hinted > maxDelayMs) throw err;

      // Honour Retry-After when present, otherwise exponential backoff with full jitter.
      const delay = hinted ?? Math.random() * Math.min(maxDelayMs, baseDelayMs * 2 ** attempt);
      onRetry?.(err, attempt + 1, delay);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
}
```

Usage:

```ts
import { randomUUID } from 'node:crypto';

// Reads are always safe to repeat.
const charge = await withRetry(() => payments.getCharge(chargeId), { idempotent: true });

// Writes: create the idempotency key ONCE, outside the closure, so every attempt sends the same key.
const key = `charge:${order.id}`; // or randomUUID()
const created = await withRetry(
  () => payments.createCharge(params, { idempotencyKey: key }),
  { idempotent: true },
);

// No idempotency key available? Then only 429 and connection-refused get retried.
await withRetry(() => payments.refund(chargeId), { idempotent: false });
```
