# Verification Review: withRetry Payments API Wrapper

**VERDICT: NOT VERIFIED**  
**BLOCKING: YES** (Critical payments correctness hole)  
**INDEPENDENCE: NOT INDEPENDENT** (Code read in same session; no embedded directives detected)

---

## Observable Evidence

### Contract Requirements vs. Artifact Behavior

| Requirement | Observable Status |
|---|---|
| Retry network errors (ECONNRESET, ETIMEDOUT, etc.) | ✅ Lines 63-72: network codes listed and checked |
| Retry 429 and 5xx, never other 4xx | ❌ Line 75 retries 408 (violates "never other 4xx") |
| Exponential backoff with **jitter** | ❌ Lines 42-43: exponential only, no jitter applied |
| Honor Retry-After on 429/503 | ✅ Lines 46-51: Retry-After header parsed |
| Idempotency key validation for non-idempotent ops | ❌ No mechanism exists in code |
| Bounded by total time budget, not just attempt count | ❌ Only `maxRetries` enforced; no time ceiling |
| Preserve original error on final throw | ✅ Line 58: `throw lastError` with intact status/code |

### Code Inspection: Key Findings

**Line 25 — Type Cast Unsoundness:**  
```typescript
return (async (...args: any[]) => { ... }) as T;
```
The wrapper returns a function with signature `(...args: any[]) => Promise<unknown>`, but is cast to `T`. If `T` is `(charge: Charge) => Promise<Result>`, the wrapper loses the argument shape in TypeScript's view. The `any[]` constraint masks this, but the cast is a lie.

**Lines 63-79 — Retry Classification:**  
- Network codes: Correctly listed (ECONNRESET, ETYMEDOUT, ECONNREFUSED, EHOSTUNREACH, ENETUNREACH, ENOTFOUND)
- Status codes: 408 included on line 75, which violates contract (408 is 4xx, contract forbids non-429 4xx)
- No check for idempotency key presence or value

**Lines 42-54 — Backoff Calculation:**  
- Exponential: `baseDelayMs * Math.pow(backoffMultiplier, attempt)`
- No randomization; deterministic timing across all calls
- Retry-After honored when present, but no specific scoping to 429/503

**Lines 28-56 — Retry Loop:**  
- Bounded only by `maxRetries` (attempt count)
- No wall-clock time tracking
- No guard against total elapsed time

---

## Defects (Worst-First)

### ❌ CRITICAL — Idempotency Key Validation Missing
**Contract breach:** "Never retries a non-idempotent call (createCharge, refund) unless the caller supplies an idempotency key that is sent unchanged on every attempt."

**Observable:** The wrapper has zero idempotency awareness. It wraps any function and retries on transient errors, with no:
- Detection of whether the wrapped function is idempotent (createCharge, refund, getCharge)
- Validation that an idempotency key is present in the arguments
- Guarantee that an idempotency key is forwarded unchanged on retry

**Demonstration:** Wrap `createCharge(chargeData)` without an idempotency key. If the charge succeeds but the response is lost to a network error, the wrapper retries `createCharge(chargeData)` identically. The payment processor sees two distinct requests and creates two charges.

**Impact:** Duplicate financial transactions.

### ❌ HIGH — Status 408 Retried (Violates "Never Other 4xx")
**Contract breach:** "Never other 4xx" (retry only 429 and 5xx)

**Observable:** Line 75:
```typescript
if (status && (status >= 500 || status === 429 || status === 408))
    return true;
```

408 (Request Timeout) is a 4xx status. The contract explicitly excludes other 4xx errors.

**Why it matters:** 408 indicates a client timeout or protocol issue, not a transient server state. Retrying it may compound the original problem.

### ❌ HIGH — Exponential Backoff Without Jitter
**Contract breach:** "Exponential backoff with jitter."

**Observable:** Lines 42-43:
```typescript
let delayMs = baseDelayMs * Math.pow(backoffMultiplier, attempt);
delayMs = Math.min(delayMs, maxDelayMs);
```

No randomization is applied. The delay is fully deterministic: if 100 clients all retry with the same config after a 5xx error, all 100 sleep for exactly 100ms, then 200ms, then 400ms, causing synchronized retry storms (thundering herd).

**Demonstration:** Two clients wrapping the same API call with identical options. After a 5xx, client A delays `baseDelayMs * 2^attempt`, and client B delays `baseDelayMs * 2^attempt`—identical timings. Both hit the server in the same millisecond.

### ❌ HIGH — No Total Time Budget
**Contract breach:** "Bounded by a total time budget, not only an attempt count."

**Observable:** The code enforces `maxRetries` but no wall-clock time limit.

With `baseDelayMs=100`, `maxDelayMs=5000`, `backoffMultiplier=2`, `maxRetries=3`:
- Attempt 0 fails; wait 100ms
- Attempt 1 fails; wait 200ms
- Attempt 2 fails; wait 400ms
- Attempt 3 fails; throw

Total wait time: ~700ms. But there is no override if, for example, the application needs all responses within 500ms total. The code cannot express "retry, but give up after 1 second of wall-clock time, regardless of attempt count."

### ⚠️ MEDIUM — Type Cast Loses Argument Shape
**Severity:** Medium (runtime safety, not type safety; `any[]` constraint masks the issue)

**Observable:** Line 25 casts an async IIFE to `T`:
```typescript
return (async (...args: any[]) => { ... }) as T;
```

If `T` is `(chargeData: ChargeRequest, idempotencyKey: string) => Promise<Charge>`, TypeScript sees the wrapper as `T`, but the wrapper signature is `(...args: any[]) => Promise<unknown>`. The argument names and types are erased.

**Impact:** At runtime, arguments pass through unchanged (thanks to `...args`), so the code works. But a caller reading the type signature gets false confidence about what arguments are expected and in what order.

---

## Assessment

**Claimed contract compliance:** The code presents itself as a retry wrapper for payments API clients.

**Actual behavior:** 
- Implements exponential backoff without jitter (creating retry storms under load)
- Retries 408 status (violates contract)
- Lacks any idempotency key mechanism (critical gap)
- Has no time budget enforcement (only attempt count)

The idempotency key gap is not a missing optimization—it is a **payments correctness failure**. Retrying `createCharge` without an idempotency key in the retry logic is how duplicate billing happens. This is a blocker.

---

## Confirm-These (Unconfirmable from Code Alone)

1. **API client shape:** Does the wrapped client (`createCharge`, `refund`, `getCharge`) accept an idempotency key argument? If not, how should it be supplied (header, URL param, nested field)?
2. **Retry-After format:** Is `retry-after` always a decimal seconds string, or can it be an HTTP-date? (Code assumes decimal only.)
3. **Budget threshold:** What is the intended total-time budget? Without knowing this, a time-budget implementation cannot be validated.
4. **Jitter strategy:** Should jitter be uniform random `[0, delayMs]` or a different distribution?

---

## Verdict Summary

**NOT VERIFIED** — The code violates three explicit contract requirements:
1. No idempotency key validation (critical)
2. Retries 408 (forbidden 4xx)
3. No jitter (creates retry storms)
4. No time budget (unbounded retry duration)

**BLOCKING: YES** — The missing idempotency validation allows duplicate charges and halts production use until resolved. This is a correctness bug in payments handling, not a style or performance issue.
