# T2 judgment: withRetry (payments client)

Contract (contract-t2.txt), numbered for reference:
- C1 Retry only network errors, 429, 5xx. Never other 4xx.
- C2 Never retry non-idempotent calls (createCharge, refund) unless the caller supplies an idempotency key sent unchanged every attempt. Reads may retry freely.
- C3 Exponential backoff with jitter. Honors Retry-After on 429/503.
- C4 Bounded by a total time budget, not only an attempt count.
- C5 After the last attempt, the original error reaches the caller unchanged.

---

## Artifact 1: sr-t2-frontier.md

### Ground truth (written before reading the reviews)

| id | sev | defect |
|---|---|---|
| F-D1 | HIGH | C2 breach. `isRetryable` returns true for `status === 429` (line 31) and for `ECONNREFUSED`/`EAI_AGAIN` (line 32) before the `if (!idempotent) return false` check (line 33). So `{ idempotent: false }` createCharge/refund calls with no key still get retried. The usage block (line 93-94) does exactly this with `refund`. "Server never processed it" is a reasonable argument, but the contract says "never". |
| F-D2 | MEDIUM | C2 unenforced. The gate is a caller-asserted boolean. The wrapper never sees, requires, or pins an idempotency key, so `idempotent: true` on a keyless createCharge, or with `randomUUID()` generated inside the closure, gets ECONNRESET/ETIMEDOUT/5xx retried. That is the double-charge path. |
| F-D3 | HIGH | C4 breach. No total time budget: no deadline, no elapsed-time check, no per-attempt timeout on `fn()`. Bounds are only `retries` (a count) and `maxDelayMs` (one sleep's cap). A slow or hung `fn` makes wall time unbounded. |

Checked and clean on my pass: no other 4xx is retried (429 is the only 4xx match). Backoff is exponential with full jitter (line 70). Retry-After handles seconds and HTTP-date, `Headers` and plain records, clamps negatives. Giving up when Retry-After > maxDelayMs never retries early, so it satisfies "honors". `throw err` rethrows the original object. The 5xx set {500,502,503,504} is narrower than "5xx" but does not breach "retries only". I did not count that.

Added from the reviews (valid, I missed them):
| id | sev | defect |
|---|---|---|
| F-D4 | LOW | `onRetry` is called unguarded inside `catch` (line 71). If it throws, the callback's error replaces the payments error and retrying stops. That violates C5 in spirit on a caller-controlled path. |
| F-D5 | LOW | Options are not validated. `retries: NaN`/`Infinity` means `attempt >= retries` is never true, so a persistent 429 retries forever (and F-D3 means nothing else stops it). `baseDelayMs: NaN` gives ~0 ms sleeps. |

Not counted, neutral: plain-object header lookup only matches `retry-after`/`Retry-After`. Both reviews raised this as LOW or confirm-only. Hinted delays get no jitter. Possible `err.cause.code` placement is a client question, not a defect in this code.

### Review A
- Found: F-D1, F-D2, F-D3, F-D4, F-D5.
- Missed: none.
- FALSE CLEAN: none. The clean axes (other 4xx, error identity, full jitter, Retry-After parsing) are all correct, and the onRetry exception is carved out.
- False positives: none in the code. Unverifiable: it attacks a cover-letter claim, "Worst-case added wait with the defaults is about 1.4s", and quotes "I haven't compiled or run this". Neither appears in the artifact I was given. It may have had a cover letter I don't have. Not scored against it, but not credited either.
- Verdict: NOT VERIFIED, BLOCKING. Correct.
- Severity: rates F-D2 HIGH (I rate it MEDIUM). Defensible on a payments path.

### Review B
- Found: F-D1, F-D2, F-D3, F-D4, F-D5.
- Missed: none.
- FALSE CLEAN: none.
- False positives: none. It rates onRetry and NaN as MEDIUM where I rate LOW. That is severity inflation, not a false defect.
- Verdict: NOT VERIFIED, BLOCKING. Correct.
- Extras: line-cited throughout. It correctly notes that `maxDelayMs: NaN` also disables the long-Retry-After guard, and that `UND_ERR_CONNECT_TIMEOUT` belongs in NOT_PROCESSED by the file's own logic. Both are valid LOW observations.

### More accurate for Artifact 1: tie
Both found the same five defects with the same verdict and no false cleans. B's line citations are slightly tighter, and A's one extra claim can't be checked against the artifact.

---

## Artifact 2: sr-t2-haiku.md

### Ground truth (written before reading the reviews)

| id | sev | defect |
|---|---|---|
| H-D1 | HIGH | C2 breach. There is no idempotency concept at all: no flag, no key, no per-method policy. createCharge/refund are retried on ECONNRESET/ETIMEDOUT/5xx, so a lost response means a double charge or double refund. |
| H-D2 | HIGH | C4 breach. No total time budget, only `maxRetries`. No timeout on `fn`. |
| H-D3 | MEDIUM | C3 breach. No jitter: `baseDelayMs * backoffMultiplier^attempt`, deterministic. |
| H-D4 | MEDIUM | C1 breach. `status === 408` is retried (line 75). That is a 4xx other than 429, which the contract says never to retry. |
| H-D5 | MEDIUM | The Retry-After override is uncapped. `delayMs = seconds * 1000` replaces the value after the `Math.min(…, maxDelayMs)` cap, so `Retry-After: 3600` sleeps one hour. That makes H-D2 worse. |
| H-D6 | MEDIUM | C3 "honors Retry-After" is only partly met. The HTTP-date form is ignored: `parseInt("Wed, 21 Oct…")` is NaN, so it falls back to backoff and can retry before the server's date. A fetch `Headers` instance makes `error.headers['retry-after']` undefined, so Retry-After is ignored entirely. The key lookup is case-sensitive, so `Retry-After` in a plain record is missed. |
| H-D7 | LOW | `fn(...args)` is invoked without a `this`. `withRetry(payments.createCharge)` on a class-method client loses its receiver. |
| H-D8 | LOW | `ENOTFOUND` is retried. It is usually a permanent DNS failure, not one that "can succeed on retry". |
| H-D9 | LOW | `maxRetries` < 0 or NaN means the loop never runs and `throw lastError` throws `null`. `fn` is never called and the caller gets `null` instead of an error. |

Checked and clean: the original error object is rethrown unchanged (line 39 and line 58, same reference). Other 4xx besides 408 and 429 are not retried.

### Review A
- Found: H-D1, H-D2, H-D3, H-D4. H-D6 is raised only as a confirm-these item ("Code assumes decimal only"), not as a defect.
- Missed: H-D5, H-D6 (as a defect), H-D7, H-D8, H-D9.
- FALSE CLEAN: the table row `| Honor Retry-After on 429/503 | ✅ Lines 46-51: Retry-After header parsed |` passes an axis that contains H-D5 and H-D6. Its own confirm-these item half-contradicts that check mark.
- False positives: "MEDIUM — Type Cast Loses Argument Shape … The argument names and types are erased." That is wrong. `as T` makes callers see exactly T's signature, and args pass through unchanged, so caller-facing types are accurate. At most it is an internal `any` looseness, not a defect. Minor inaccuracies: the typo "ETYMEDOUT", and the time-budget arithmetic (~700 ms) ignores Retry-After.
- Verdict: NOT VERIFIED, BLOCKING. Correct.

### Review B
- Found: H-D1, H-D2, H-D3. It partly touches H-D5 ("a Retry-After that could be 60+ seconds, total elapsed time is unbounded"), but only under the budget defect and without seeing that the cap is bypassed.
- Missed: H-D4, H-D6, H-D7, H-D8, H-D9 (and H-D5 as its own defect).
- FALSE CLEAN, two:
  1. "✅ Retries only transient errors: … plus 5xx, 429, and 408. It does NOT retry other 4xx codes. This axis is clean." It names 408 and still passes the axis. H-D4 is a direct contract breach.
  2. "✅ Honors Retry-After: On 429 or 503, the code reads the Retry-After header and uses it to override the backoff delay. This axis is clean." This passes an axis that contains H-D5 and H-D6.
- False positives: none of substance. Minor inaccuracies: "Line 34 calculates delayMs" (the actual line is 42). The demo invents `createChargeWithRetry(userId, 100)`. It quotes a "Claimed: zero-dependency retry wrapper … drops in front of existing client methods" that is not in the artifact I was given.
- Verdict: NOT VERIFIED, BLOCKING. Correct.

### More accurate for Artifact 2: Review A
A caught the 408 contract breach, which B explicitly certified clean, and A has one false clean to B's two. A's type-cast false positive costs less than B's two false cleans.

---

## Cross-artifact notes
- All four reviews gave the correct verdict. The spread is in coverage and false cleans.
- On Artifact 2, both reviews missed the fetch-`Headers` and HTTP-date gaps in Retry-After handling, the uncapped Retry-After sleep as its own defect, the lost `this` binding, and the `throw null` edge case.
- Two frontier-artifact reviews and one haiku-artifact review quote producer claims (cover letter text) that are absent from the artifacts supplied to this judge. Either the reviewers saw extra material, or they invented it. That should be checked against the reviewer inputs.
