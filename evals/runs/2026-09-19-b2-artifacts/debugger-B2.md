# Debug: Invoice Page TypeError on 3% of Loads

## Failure
**Expected:** `renderInvoiceLines` receives an array from the parent `InvoiceTable` component and maps over it without error.

**Actual:** `TypeError: Cannot read properties of undefined (reading 'map')` at `invoice-table.tsx:88` in `renderInvoiceLines`.

**Trigger condition:** Intermittent — about 3% of invoice page loads, started around 2026-09-12 (last Thursday) when the invoice fetch moved into a server component.

---

## Reproduction
**Minimal case needed:** 
- Load the invoice page 50+ times and record which loads fail (statistically should see 1-2 failures). 
- On failure: capture browser network tab, server logs, and the exact request/response that accompanied it. 
- Current blocker: no reproducible case available; the 3% rate suggests a race condition or async edge case.

**To get evidence faster:**
- Add a console.error() with the actual value passed to `renderInvoiceLines` before it fails — this will capture what's being passed instead of undefined.
- Enable server component error logging to see if the fetch is throwing or returning null/undefined.

---

## Hypotheses (Ranked by Likelihood × Cost-to-Test)

### 1. Server Component Promise Race Condition — **HIGH confidence, CHEAP to test**
**Cause:** The server component fetch is async. The client component renders before the data arrives, passing `undefined` to `renderInvoiceLines`.

**Why plausible:** The timing of the change (fetch moved to server component) is the pivot point. Server components return promises; the data transfer between server and client is now async where it may have been sync before.

**Cheapest probe:** 
- Check if there's a Suspense boundary wrapping the `InvoiceTable` component. If not, the client is rendering before the promise resolves.
- Log the value passed to `renderInvoiceLines` on the client side (before line 88). A console.error() or throw in a try-catch will show what's actually being received.
- Search the git diff from last Thursday for where the fetch moved — confirm whether there's error handling for the async boundary.

---

### 2. Missing Null/Undefined Guard at Line 88 — **HIGH confidence, CHEAP to test**
**Cause:** `renderInvoiceLines` assumes its input is always an array and calls `.map()` without checking. The server component now sometimes passes `undefined` (either explicitly or via error swallowing).

**Why plausible:** Server component error handling may not be routing errors clearly to the client. A fetch failure (network error, 500, etc.) silently becomes `undefined` instead of being caught and re-thrown.

**Cheapest probe:**
- Read `invoice-table.tsx:88` and the surrounding 5–10 lines. Look for `.map()` being called on an unchecked variable.
- Check what `InvoiceTable` receives from the server component and whether it validates before passing to `renderInvoiceLines`.
- Look for try-catch or error handling in the server component fetch; if there's no error re-throw or explicit error state, the fetch failure is being swallowed.

---

### 3. Server Component Fetch Error Not Caught — **MEDIUM-HIGH confidence, MEDIUM cost**
**Cause:** The server component fetch throws or returns an error status. The error isn't caught, and an undefined value is passed downstream instead.

**Why plausible:** Moving logic to a server component often exposes error paths that weren't visible before. If the error boundary or error handling wasn't updated alongside the refactor, fetch failures silently become undefined.

**Cheapest probe:**
- Check the server component's error handling: is there a try-catch? If yes, what does the catch block do? Does it re-throw, return null, or silently continue?
- Check server logs from times when the page loads fail — look for 4xx/5xx responses or timeout errors.
- Add explicit logging in the server component: `console.log("Fetched invoices:", data)` right after the fetch, before returning.

---

### 4. Cache Invalidation or Stale State — **MEDIUM confidence, HIGHER cost**
**Cause:** The data is cached somewhere (server-side cache, Redis, component state). Cache is invalidated mid-render or misaligned between requests.

**Why plausible:** If last Thursday's refactor introduced caching to avoid refetching, and the invalidation logic is off, a cache miss could return `undefined`.

**Cheapest probe:**
- Search the git diff from last Thursday for any cache-related code (fetch wrappers, memoization, unstable_cache, etc.).
- Check if the fetch is wrapped in `unstable_cache()` (Next.js server component feature). If yes, review the cache revalidation rules.
- Monitor cache hit/miss rates correlating to the 3% failure rate.

---

### 5. Type Mismatch or Incomplete Type Definition — **MEDIUM confidence, MEDIUM cost**
**Cause:** TypeScript types are incorrect or incomplete. At runtime, the prop is a different shape than the types promise.

**Why less likely first:** TypeScript would catch this during type-check (unless types are `any` or `unknown`). But possible if the refactor introduced a type gap.

**Cheapest probe:**
- Check the type of the prop passed to `renderInvoiceLines`. Is it `Array | undefined`? If it's just `Array`, that's the gap.
- Run `tsc --noEmit` and look for any type errors that might have been missed.
- Check if the server component's return type matches what the client expects.

---

## Most Likely Root Cause
**Hypothesis 1 + 2 together, HIGH confidence:**

The server component fetch is now async. The client component renders **before the promise resolves**, passing `undefined` (or an error state that wasn't validated). Line 88 in `renderInvoiceLines` calls `.map()` on this undefined value without checking.

**Why this explains all the evidence:**
- The timing (started when fetch moved to server component) is the pivot.
- Intermittency (3%) matches race condition behavior: sometimes the client renders before the fetch completes, sometimes it doesn't.
- No reproduction case needed: it's purely timing-dependent.

**Proof this is right:** If you add a `?.` (optional chaining) or a guard clause at line 88 (`if (!data) return null;`), the error will disappear. **But that's not the root cause — that's the symptom.** The root cause is that the data is arriving undefined when it shouldn't be. Masking it will hide a real data loss bug.

---

## What Would Prove Me Wrong
- If server logs show the fetch succeeds and returns valid data every time, but the client still receives undefined → the bug is in the server-to-client serialization, not the fetch.
- If the error happens even with a Suspense boundary and proper async handling → the problem is not a race condition, but something else mutating or clearing the data after it arrives.
- If disabling the cache (if one exists) eliminates the errors → the bug is cache invalidation, not async timing.

---

## Recommended Next Step
1. **Instrument the code:** Add logging to capture the actual value passed to `renderInvoiceLines` when the error occurs.
2. **Check the git diff:** Review exactly what changed in the fetch refactor — where did the promise live before, and where does it live now?
3. **Verify async boundaries:** Confirm there's a Suspense boundary or async error boundary wrapping the component, or that the client is properly awaiting the server data.
4. **Run a targeted test:** Load the page 50 times with network throttling enabled (to increase the 3% to something more observable), and capture the first failure to see what's in the network response.
