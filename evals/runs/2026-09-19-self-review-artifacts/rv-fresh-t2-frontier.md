# Verification: `withRetry` (with-retry.ts) against the payments retry contract

## Verdict

**NOT VERIFIED. BLOCKING: yes.**

Three HIGH defects break the contract. The wrapper has no total time budget. It cannot see the idempotency key, so it cannot enforce the key condition. And it retries non-idempotent calls that have no key (on 429 and on connection-refused/DNS errors), which the contract says must never happen.

**Most damaging defect:** the idempotency guarantee rests entirely on a boolean the caller asserts. `withRetry` receives `() => Promise<T>` and never sees an idempotency key. So `withRetry(() => payments.createCharge(params), { idempotent: true })`, with no key, retries `createCharge` after a 503 or ECONNRESET that may already have charged the card. The same happens when a key is generated inside the closure. The contract says the call must not be retried "unless the caller supplies an idempotency key that is sent unchanged on every attempt", and nothing in this code checks that.

## Independence

**INDEPENDENT.** I saw only the finished artifact and the contract. I did not write, draft, or revise it, and I did not see the builder's reasoning. Limitation: the check was static. I had Read access only, so every "demonstration" below is a line-by-line trace, not an executed test.

## Observable evidence

These can be pointed at directly in the artifact:

- **No total time budget exists.** `withRetry` (lines 56-75) never reads a clock and never compares elapsed time to anything. It takes no deadline or budget option and no `AbortSignal`, and it puts no timeout on `fn()`. The only `Date.now()` is inside the Retry-After date parser (line 53). The only limits are `attempt >= retries` (line 63) and a per-sleep cap, `maxDelayMs` (lines 67, 70).
- **The key is invisible to the wrapper.** `RetryOptions` has no key field (lines 9-20), and `fn` takes no arguments (line 56). The comment on `idempotent` (lines 11-14) puts the whole key requirement on the caller.
- **Keyless non-idempotent retries are deliberate.** Line 31 returns `true` for 429 before the `idempotent` check. Line 32 does the same for `ECONNREFUSED` and `EAI_AGAIN`. Line 33 (`if (!idempotent) return false`) only runs after both. The usage block says so: "No idempotency key available? Then only 429 and connection-refused get retried." (line 93, followed by `refund` with `idempotent: false`).
- **Numeric options are not validated.** `retries` falls back to its default only when it is `undefined` (line 57). `attempt >= NaN` is always false, so `retries: NaN` retries forever.
- **The original error survives both exit paths.** `throw err` at line 63 and at line 67 rethrows the same object. Status, code and headers are untouched.
- **Other 4xx statuses are never retried.** Among 4xx statuses, only `status === 429` (line 31) can make `isRetryable` return true. `AMBIGUOUS_STATUSES` is {500, 502, 503, 504}.
- **The artifact contains no embedded instructions** addressed to a reviewer.
- **No test or build results were supplied.**

## Assessment (judgment, not demonstrated)

- The builder's reasoning that 429 and ECONNREFUSED mean "not processed" is sound for ECONNREFUSED and EAI_AGAIN: no connection was made, or the name never resolved. For 429 it is an assumption about the server. A 429 is usually a rejection before processing, but that depends on which component sends it: the API, a gateway, or a lock-contention path. The contract does not grant that exception either way. I rate the keyless-retry breach HIGH because the contract says "never" and the impact is a duplicate payment or refund. The likelihood is low for ECONNREFUSED and unknown for 429.
- `maxDelayMs` doing double duty as a budget stand-in (a Retry-After above it causes an immediate throw) shows the builder was thinking about latency. It still bounds each individual sleep, not the total wall time.
- A hung `fn()` is the realistic way the missing budget bites. A payments call that never settles is never timed out, and up to 4 attempts plus 3 sleeps of up to 5 s each can stack behind it.

## Defects (worst-first)

❌ **HIGH: the idempotency-key condition is unenforced (stored nowhere, checked nowhere).**
Contract breach: a non-idempotent call may retry only if the caller supplies a key that is sent unchanged on every attempt. `withRetry` accepts `idempotent: true` as a bare assertion and cannot know whether a key exists or stays stable.
How to demonstrate: `withRetry(() => payments.createCharge(params), { idempotent: true })` with no key. Have the first attempt reach the server, commit the charge, and then return 503 or drop the socket (ECONNRESET). `isRetryable` returns true (lines 34-37) and `createCharge` runs again, creating a second charge. The same result follows from `withRetry(() => payments.createCharge(params, { idempotencyKey: randomUUID() }), { idempotent: true })`: the key is regenerated on every attempt, so the server deduplicates nothing. The usage comment `// or randomUUID()` (line 87) is correct only because that key sits outside the closure, and it is one refactor away from this bug.

❌ **HIGH: there is no total time budget. Retries are bounded only by attempt count.**
Contract breach: "Bounded by a total time budget, not only an attempt count."
How to demonstrate: stub `fn` to take 30 s and then reject with ETIMEDOUT on an idempotent call. With defaults, `withRetry` runs 4 attempts plus 3 jittered sleeps, about 120 s or more, and nothing stops it. Stub `fn` to never settle and `withRetry` never returns. No option exists that a caller could set to prevent either case.

❌ **HIGH: non-idempotent calls with no key are retried on 429, ECONNREFUSED and EAI_AGAIN.**
Contract breach: "Never retries a non-idempotent call (createCharge, refund) unless the caller supplies an idempotency key."
How to demonstrate: `withRetry(() => payments.refund(chargeId), { idempotent: false })`. Have the first attempt reject with `{ status: 429 }`. Line 31 returns true, and `refund` is called a second time with no idempotency key. The usage block on line 93 documents exactly this behavior.

❌ **MEDIUM: invalid numeric options produce unbounded or hot retry loops.**
Contract breach: the bound is lost, and the missing time budget (above) means nothing else catches it.
How to demonstrate: `retries: NaN`, for example `Number(process.env.RETRIES)` when the variable is unset, makes `attempt >= retries` always false (line 63), so a persistent 429 retries forever. `retries: Infinity` behaves the same way. `baseDelayMs: NaN` or `maxDelayMs: NaN` makes `delay` NaN (line 70), which `setTimeout` treats as about 1 ms, so the loop becomes a tight hammer on the payments API. With `maxDelayMs: NaN`, `hinted > NaN` is also false, so the long-Retry-After guard stops working.

❌ **MEDIUM: an exception thrown by `onRetry` replaces the payment error and stops retrying.**
Contract breach: the caller gets the callback's error instead of the original one, with status and code lost. This happens mid-sequence rather than "after the last attempt", but it is still a path where the payment error never reaches the caller.
How to demonstrate: pass `onRetry: () => { throw new Error('logger down') }`. The first retryable 503 on a read reaches line 71. The throw escapes the `catch` block, and the caller receives `Error('logger down')` with no `status` or `code`.

⚠️ **LOW: the set of retried failures is narrower than "network errors ... and similar" and "5xx".**
- 5xx: 507, 508 and 520-599 (for example the 520-524 codes proxies emit) are never retried. Excluding 501 and 505 is defensible, since those cannot succeed on retry.
- Network: `EHOSTUNREACH`, `ENETUNREACH`, `UND_ERR_CONNECT_TIMEOUT`, `UND_ERR_HEADERS_TIMEOUT` and `UND_ERR_BODY_TIMEOUT` are missing. `UND_ERR_CONNECT_TIMEOUT` means no connection was made, so it belongs in `NOT_PROCESSED_CODES` by the file's own logic.
- If the client is fetch/undici-based and does not flatten errors, the code is on `err.cause.code`, not `err.code`. Line 30 then sees no code and retries no network error at all. This depends on the client (see Confirm-these).
Under-retrying does not breach "retries **only**", but it does fall short of the listed retry set.

⚠️ **LOW: Retry-After handling edge cases.**
- For plain-object headers, only the keys `retry-after` and `Retry-After` are checked (line 47), so `RETRY-AFTER` is missed.
- Hinted delays get no jitter (line 70), so many clients told `Retry-After: 1` retry at the same moment.
- Retry-After is honored on any retryable error, not only 429/503. This is harmless.

⚠️ **WEAK: a Retry-After above `maxDelayMs` means an immediate give-up (line 67).**
With defaults, a 429 carrying `Retry-After: 6` fails at once and is never retried. It does not violate "honors Retry-After" (the wrapper never retries early), but it is a per-sleep cap standing in for the budget the contract asks for, and it makes 429 retries depend on a server hint staying under 5 s.

✅ **Other 4xx statuses are never retried** (line 31 plus `AMBIGUOUS_STATUSES`).
✅ **The original error reaches the caller unchanged** on both normal exit paths (lines 63, 67), apart from the `onRetry` path above.
✅ **Exponential backoff with full jitter** on the unhinted path: `random() * min(maxDelayMs, baseDelayMs * 2^attempt)` (line 70).
✅ **Retry-After parsing** handles delta-seconds and HTTP-date formats, clamps negative values to 0, supports `Headers`-like objects with `.get` and plain records, and handles array values (lines 41-54).
✅ **Reads retry freely** on 429, 500/502/503/504 and the listed socket codes when `idempotent: true`.
✅ **The attempt count matches its documentation:** `retries = 3` means 4 attempts in total.
✅ **Null or non-object throws** are handled: `(err ?? {})` on line 30, optional chaining on line 42.

## Claimed vs. actual

| Claim in the artifact | What the code actually does |
|---|---|
| `idempotent` "true only if ... writes that send the SAME idempotency key", "Required on purpose, so every call site has to decide" (lines 11-14) | Forces a decision but checks nothing. A wrong `true` retries writes that may already have been processed. |
| "The server never did any work, so these are safe to retry for any call" (line 22) | True for ECONNREFUSED and EAI_AGAIN. Used to justify retrying non-idempotent calls, which the contract forbids without a key. |
| "rate limited: rejected before processing" (line 31) | An assumption about server behavior, not verified for this payments API. Also the reason keyless `refund`/`createCharge` retry on 429. |
| `maxDelayMs`: "a longer Retry-After gives up instead of waiting" (line 18) | Accurate. It caps a single sleep and is not a total budget, which the contract requires. |
| "A user is waiting on this request. If the server asks for a long pause, fail now rather than hang." (line 66) | Only prevents long sleeps. A slow or hung `fn()` still makes the caller wait without limit. |
| "No idempotency key available? Then only 429 and connection-refused get retried." (line 93) | Accurate description of the code (plus EAI_AGAIN), and a direct statement of the contract breach. |

## Confirm-these

1. **Does this payments API guarantee that a 429 is always returned before any processing?** That covers every component that can emit a 429: the API, the gateway, and any lock-contention path. If it does, the keyless-429 retry is low-risk in practice. It still breaches the contract as written, so either the contract or the code has to change.
2. **How does the client surface network errors?** The code needs to know whether `code` is at the top level or on `cause`, and what type the `headers` object is. This decides whether any network error is retried at all.
3. **Do both `createCharge` and `refund` accept idempotency keys, and does the server honor them on retry?** The usage block shows one only for `createCharge`.
4. **Does the contract's "5xx" mean every 5xx or only the transient ones?** The answer decides whether the narrower status set is a gap.
5. **No tests or runtime evidence were provided.** Every demonstration above is a static trace and should be turned into executed tests before any fix is accepted.
