=== REVIEW A ===
# Verification: `withRetry` (payments client retry helper)

## Verdict

**NOT VERIFIED. BLOCKING: yes.**

Three HIGH defects break the stated contract. Two of them are on the payment-safety clause and one on the total-time-budget clause.

**Single most damaging defect:** the helper cannot enforce the idempotency-key clause. It never sees a key, so `idempotent: true` is a claim the caller makes and nobody checks. A closure that creates a fresh key on every attempt gets ambiguous failures retried, and a second charge is possible. Separately, `idempotent: false` still retries `createCharge` and `refund` without any key on 429, `ECONNREFUSED` and `EAI_AGAIN`. The contract says "never."



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

=== REVIEW B ===
# Verification: `withRetry` (with-retry.ts) against the payments retry contract

## Verdict

**NOT VERIFIED. BLOCKING: yes.**

Three HIGH defects break the contract. The wrapper has no total time budget. It cannot see the idempotency key, so it cannot enforce the key condition. And it retries non-idempotent calls that have no key (on 429 and on connection-refused/DNS errors), which the contract says must never happen.

**Most damaging defect:** the idempotency guarantee rests entirely on a boolean the caller asserts. `withRetry` receives `() => Promise<T>` and never sees an idempotency key. So `withRetry(() => payments.createCharge(params), { idempotent: true })`, with no key, retries `createCharge` after a 503 or ECONNRESET that may already have charged the card. The same happens when a key is generated inside the closure. The contract says the call must not be retried "unless the caller supplies an idempotency key that is sent unchanged on every attempt", and nothing in this code checks that.



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
