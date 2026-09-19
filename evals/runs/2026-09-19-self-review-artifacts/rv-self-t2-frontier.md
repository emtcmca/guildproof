# Verification: `withRetry` (payments client retry helper)

## Verdict

**NOT VERIFIED. BLOCKING: yes.**

Three HIGH defects break the stated contract. Two of them are on the payment-safety clause and one on the total-time-budget clause.

**Single most damaging defect:** the helper cannot enforce the idempotency-key clause. It never sees a key, so `idempotent: true` is a claim the caller makes and nobody checks. A closure that creates a fresh key on every attempt gets ambiguous failures retried, and a second charge is possible. Separately, `idempotent: false` still retries `createCharge` and `refund` without any key on 429, `ECONNREFUSED` and `EAI_AGAIN`. The contract says "never."

## Independence

**NOT INDEPENDENT.** The artifact was written earlier in this same conversation by the same agent that is now verifying it. This verifier has read the builder's reasoning and inherited its blind spots. Treat this as a weaker check than an independent one. For an independent check, paste the artifact and the contract below into a fresh conversation.

## Contract checked (as supplied by the coordinator)

1. Retries only failures that can succeed on retry: network errors (ECONNRESET, ETIMEDOUT and similar), 429, and 5xx. Never other 4xx.
2. Never retries a non-idempotent call (createCharge, refund) unless the caller supplies an idempotency key that is sent unchanged on every attempt. Reads (getCharge) may retry freely.
3. Exponential backoff with jitter. Honors Retry-After on 429/503.
4. Bounded by a total time budget, not only an attempt count.
5. After the last attempt, the original error reaches the caller unchanged (status, code intact).

## Observable evidence

These can be shown directly from the source.

- **Contract 4 is absent.** `withRetry` contains no deadline, no `Date.now()` budget, no elapsed-time check and no per-attempt timeout. The only bounds are `retries` (a count) and `maxDelayMs` (a cap on each individual sleep). A `fn()` that hangs is awaited forever, and total wall time is `(retries + 1) × client timeout + sum of sleeps`, with nothing limiting it.
- **Contract 2 is breached for non-idempotent calls.** In `isRetryable`, `status === 429` and `NOT_PROCESSED_CODES` (`ECONNREFUSED`, `EAI_AGAIN`) return `true` before the `idempotent` check is reached. So `withRetry(() => payments.createCharge(p), { idempotent: false })` retries on a 429 with no idempotency key present. The producer's own usage example does exactly this with `payments.refund`.
- **Contract 2 is unenforced even when `idempotent: true`.** The helper's signature is `fn: () => Promise<T>` plus a boolean. It takes no key, does not create one, and does not pass one into `fn`. Here is a demonstration by construction: `withRetry(() => payments.createCharge(p, { idempotencyKey: randomUUID() }), { idempotent: true })` sends a different key on every attempt, and the helper retries ETIMEDOUT and ECONNRESET on it. That is the double-charge path the contract exists to prevent. The only guard is a prose note in the cover letter.
- **The worst-case latency claim is false.** The cover letter says "Worst-case added wait with the defaults is about 1.4s of backoff." When Retry-After is present, `hinted` is used verbatim up to `maxDelayMs` (5000), so 3 retries can sleep about 15s. That is before counting each attempt's own duration, which is unbounded (see contract 4).
- **A thrown `onRetry` replaces the original error.** `onRetry?.(err, attempt + 1, delay)` sits inside the `catch` with no guard. If the callback throws (for example a logger failure), the caller receives the callback's error instead of the payments error, and retrying stops. This breaches the spirit of contract 5 on a path the caller controls.
- **Non-finite config gives an unbounded loop.** `retries: NaN` or `retries: Infinity` makes `attempt >= retries` never true. A persistent 429 then retries forever, and contract 4's missing budget provides no backstop. `baseDelayMs: NaN` produces `setTimeout(NaN)`, which is roughly 0ms, so the endpoint gets hammered. None of the options are validated.

### Axes checked and clean

- Other 4xx statuses are never retried. The only 4xx status that matches either status check is 429. 400, 401, 402, 403, 404, 409 and 422 all fall through to `false`.
- On exhaustion and on non-retryable errors, the original error is rethrown by identity (`throw err`). The same object reaches the caller, with `status`, `code` and `headers` intact. This holds on every path except the `onRetry` defect above.
- Backoff is exponential with full jitter: `Math.random() * Math.min(maxDelayMs, baseDelayMs * 2 ** attempt)`.
- Retry-After parsing handles delta-seconds and HTTP-date, clamps negative and past values to 0, and accepts a `Headers` object, anything Map-like with `.get`, or a plain object with array or string values.
- 503 carrying Retry-After is honored whenever the call is retried, which is only for idempotent calls. That is consistent with contract 2.
- Omitting `idempotent` from untyped JS gives `undefined`, which is falsy, so the helper fails toward the safer behavior.
- The helper has no injection sinks and no secret or PII output of its own. It logs nothing itself.

## Assessment (judgment, not demonstrated)

- The builder's justification for retrying non-idempotent calls on 429 and ECONNREFUSED is that the request was "rejected before processing." That is true by convention. It is not guaranteed across proxies, gateways or every provider. Even if the reasoning were sound, the contract says "never" without a key, so this is scored as a breach and not as a trade-off.
- Retry-After values above `maxDelayMs` make the helper give up instead of waiting. It never retries sooner than the server asked, so I judge this to satisfy "honors Retry-After." A stricter reading of the contract could disagree.
- 5xx coverage is 500, 502, 503 and 504 only. Not retrying 501 or 505 is defensible because they cannot succeed on retry. Omitting 507, 508 and similar is a literal deviation from "5xx" but low impact.
- The network-code set leaves out ENETUNREACH, EHOSTUNREACH, UND_ERR_CONNECT_TIMEOUT and UND_ERR_HEADERS_TIMEOUT. These fall inside "and similar" in the contract. This is minor, but reads would fail to retry on some real transient failures.
- There is no AbortSignal. A request whose user has disconnected keeps retrying. This is not in the contract, but it compounds the missing time budget.
- `onRetry` receives the raw error. Any PII or headers in it go wherever the caller sends them. That is the caller's responsibility and is noted only.

## Defects (worst first)

- ❌ **HIGH.** Contract 4: there is no total time budget, only an attempt count and a per-sleep cap. Demonstrate it with a `fn` that resolves after 60s and then throws ETIMEDOUT. With `idempotent: true` and the defaults, total time is about 240s plus sleeps, and nothing stops it.
- ❌ **HIGH.** Contract 2: non-idempotent calls are retried without a key. Demonstrate it with `fn` throwing `{ status: 429 }` under `{ idempotent: false }`: `fn` is called 4 times.
- ❌ **HIGH.** Contract 2: "sent unchanged on every attempt" is not enforced. The helper never receives or controls the key, and `idempotent: true` is an unchecked assertion. Demonstrate it with a closure that calls `randomUUID()` inside `fn` and throws ETIMEDOUT: each attempt sends a new key and all of them are retried.
- ❌ **MEDIUM.** Claimed vs. actual: the "about 1.4s worst-case added wait" claim does not hold when Retry-After is present (up to about 15s), and total time is unbounded regardless.
- ⚠️ **LOW.** Contract 5 (edge case): a throwing `onRetry` swallows the original error and ends retries.
- ⚠️ **LOW.** Unvalidated options: `retries` set to NaN or Infinity gives an unbounded loop, and `baseDelayMs` set to NaN gives zero-delay hammering.
- ⚠️ **LOW.** Contract 1: 5xx coverage is partial (500, 502, 503 and 504 only), and the network-code set is narrower than "and similar" suggests.
- ✅ Other 4xx are never retried.
- ✅ The original error is rethrown by identity on exhaustion and on non-retryable paths.
- ✅ Exponential backoff with full jitter.
- ✅ Retry-After parsing (seconds and date, header container shapes).

## Claimed vs. actual

| Producer claim | Actual |
|---|---|
| "Only retries ambiguous failures... when the answer is yes [idempotent]" | True for the ambiguous set. But 429, ECONNREFUSED and EAI_AGAIN are retried on non-idempotent calls regardless, and the contract forbids that without a key. |
| Usage example: `withRetry(() => payments.refund(chargeId), { idempotent: false })` described as safe | This retries a refund on 429 with no idempotency key, which contract 2 prohibits. |
| Safety depends on creating the key "ONCE, outside the closure" | Documentation only. The API does not enforce it, and a closure that creates the key inside itself passes type-checking and is retried. |
| "Worst-case added wait with the defaults is about 1.4s" | Up to about 15s of sleeping with Retry-After, and unbounded total time because there is no budget or per-attempt timeout. |
| Errors not retried "reach the caller unchanged" | True, except when `onRetry` throws. |
| "I haven't compiled or run this" | Accurate disclosure. Type-correctness is therefore unconfirmed (see below). |

## Confirm-these (unverifiable from the context given)

- **Compilation.** The code was never compiled. Whether the `Headers` global type exists depends on the project's `lib` or `@types/node` configuration.
- **Where the client puts `code`.** If it follows undici or native `fetch`, the network code is on `err.cause.code`, not `err.code`. In that case no network error is ever classified retryable, and contract 1 fails silently for every read.
- **Header casing.** If the client's plain-object headers are not lowercased (for example `RETRY-AFTER`), Retry-After is missed.
- **Idempotency-key support.** Whether the client supports idempotency keys at all, and under what option name. The usage examples assume `{ idempotencyKey }`.
- **Built-in client retries.** Whether the client already retries internally. If it does, attempts multiply.
- **What 429 means for this provider.** Whether the payments provider guarantees a 429 means the request was not processed. This matters only if the contract is relaxed to allow keyless 429 retries.
