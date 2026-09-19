=== OUTPUT W ===

# Invoice Table TypeError — Intermittent "Cannot read properties of undefined"

## The Error
```
TypeError: Cannot read properties of undefined (reading 'map')
    at renderInvoiceLines (invoice-table.tsx:88)
    at InvoiceTable (invoice-table.tsx:41)
```

**Frequency:** ~3% of page loads  
**Timing:** Started ~Thursday (when invoice fetch moved to server component)  
**No reproduction steps known**

## Root Cause Analysis

The error is reading `.map()` on an undefined value, which means:
- The code expects an array at `invoice-table.tsx:88` but is receiving `undefined`
- This is most likely `props.invoiceLines`, `data.lines`, or a similar structure that should hold the line items
- The 3% rate and recent server component migration suggest a **race condition or incomplete data hydration**

## Most Likely Causes (in order)

1. **Server component not awaiting the fetch properly**  
   When you moved the fetch into a server component, if the promise isn't being awaited or the data isn't being passed correctly to the client component, React will render with undefined props.

2. **Streaming or partial data delivery**  
   If using `React.lazy` or streaming SSR, the component may render before data is available.

3. **Race between data fetch and component render**  
   The fetch completes at different times on different requests; occasionally it hasn't finished by render time.

4. **Error boundary or fallback missing**  
   If the fetch throws, the error isn't caught and the prop falls through as undefined.

## Immediate Diagnostics

1. **Check `invoice-table.tsx:88`** — what is the exact variable/expression calling `.map()`?
2. **Check the server component**  
   - Is the fetch awaited?  
   - Is the data being passed as a prop or via context?  
   - Are there any conditional renders that might skip data passing?

3. **Add a guard at line 88:**
   ```typescript
   (lineItems || []).map(...)  // Default to empty array
   ```
   This won't fix the root cause but will stop the crash.

4. **Log the data shape before render:**
   ```typescript
   console.log('invoiceLines:', props.invoiceLines, typeof props.invoiceLines);
   ```
   Capture this in Sentry or your error logging — the 3% failures will show up.

## The Real Fix

Once you've identified what's undefined:
- If it's a server component data passing issue: ensure the fetch is awaited and the result is passed explicitly to the client component
- If it's a timing issue: use a Suspense boundary or loading state instead of crashing
- If it's an error: catch the fetch error and provide a fallback value

The fact that it started when moving to a server component strongly suggests the data transfer mechanism between server and client is incomplete. Check that the prop is being passed and that the server is not rendering before the fetch resolves.

## Minimal Reproduction Strategy

Since you can't manually reproduce it, add temporary logging and deploy to staging:
- Log `invoiceLines` at component mount
- Log the fetch response in the server component
- Monitor for the undefined case — you'll see the pattern within a few requests


=== OUTPUT X ===

## Failure

**Expected:** renderInvoiceLines renders invoice data by mapping over a lines array.

**Actual:** TypeError — undefined is not an array, .map() called on undefined at invoice-table.tsx:88.

**Trigger:** ~3% of invoice page loads, started when invoice fetch moved into a server component (last Thursday).

---

## Reproduction

**Needed:** Minimal steps to trigger this consistently, which we don't have. The intermittency (3%) is itself a clue.

To get there, we need answers to:
- Does it reproduce on every page load, or randomly?
- Is there a specific invoice ID or data shape that reproduces it?
- Does it reproduce across browsers or only in one?
- If you refresh the page when it fails, does it recover, or stay broken?

**Interim:** Add a pre-flight log to see the actual state of the data when it arrives at renderInvoiceLines.

---

## Hypotheses

### 1. Race condition in server→client serialization (HIGH confidence, LOW cost to test)

**Cause:** Server component returns invoice data, but hydration on the client doesn't happen in the order renderInvoiceLines expects. Data arrives undefined or in the wrong shape.

**Why plausible:** Moving a fetch from client to server changes when data is available and how it's serialized. Intermittency suggests a timing race — usually the data lands before render, sometimes it doesn't.

**Cheapest probe:** Add a guard log immediately before line 88:

```javascript
console.log('renderInvoiceLines called with:', invoiceData);
if (!Array.isArray(invoiceData?.lines)) {
  console.error('Expected lines array, got:', typeof invoiceData?.lines, invoiceData?.lines);
  return null; // or fallback UI
}
// then call .map()
```

This tells us what shape the data actually is when the error fires. Run one page load that fails and paste the console output.

---

### 2. Server component error handling returns undefined (HIGH confidence, MEDIUM cost)

**Cause:** The server component's fetch fails in some cases and returns undefined or an empty/malformed object instead of throwing or returning a fallback.

**Why plausible:** Server component logic might have a code path where `invoiceData` never gets set, or a catch block that swallows errors and returns undefined.

**Cheapest probe:** Inspect the server component's fetch logic:
- Does it have a try/catch? What does catch do? (Swallows? Returns undefined? Throws?)
- Does every code path return a well-formed object with a `lines` array?
- Is there a race where the component renders before the fetch completes?

Look for any `return` statement that doesn't return `{ ..., lines: [...] }`.

---

### 3. Data shape changed with server component implementation (MEDIUM confidence, MEDIUM cost)

**Cause:** The server component returns a different data structure than the client-side fetch did. For example:
- Old client fetch: `{ lines: [...] }`
- New server component: `lines: [...]` (no wrapper object)
- Or: the server component returns a Promise that never resolves

**Why plausible:** Migrating logic often introduces subtle shape mismatches.

**Cheapest probe:** Compare the server component's return type with how renderInvoiceLines consumes it.
- What does the server component actually return?
- What properties is renderInvoiceLines trying to access?
- Is there a type mismatch?

Also: check if the server component is properly awaited in the JSX, or if there's an unawaited Promise being passed down.

---

### 4. Async timing: component renders before data loads (MEDIUM confidence, LOW cost)

**Cause:** renderInvoiceLines is called before the server component's promise resolves, receiving undefined instead of data.

**Why plausible:** If the server component's async work isn't properly sequenced with the render.

**Cheapest probe:** Verify the server component uses `await` on the fetch. Confirm the component doesn't render children until data is available.

---

### 5. Browser cache or old data structure still loading (LOW confidence, LOW cost)

**Cause:** Cached JavaScript or data from before the migration is loading in some browsers.

**Why plausible:** Intermittency could indicate stale cache.

**Cheapest probe:** Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R), clear site data in DevTools, and test again. Check if the error goes away.

---

## Most Likely

**Hypothesis 1: Race condition in server→client serialization** is the lead theory.

**Why:** 
- Intermittency (3%) is classic timing race behavior — usually the data lands before render, sometimes it doesn't.
- Server components introduce serialization boundaries that didn't exist when the fetch was client-side.
- The error is specifically "undefined is not an array," not "undefined has no property lines" — this suggests the whole data object might sometimes be undefined, not just a property.

**What it explains:**
- Why it's intermittent: Network timing varies; sometimes the server finishes serialization and hydration before render, sometimes not.
- Why it started when the fetch moved: Server components change the data flow fundamentally.
- The error location: renderInvoiceLines is called with data that's undefined.

**What would prove me wrong:**
- If the error is actually deterministic (always at the same invoice ID, always when a certain field is present). That points to shape mismatch, not timing.
- If the server component's logic has a definite code path that returns undefined (like an uncaught error or an early return). That shifts us to hypothesis 2.

---

## Next Steps

Start with the console log probe in hypothesis 1. One failed page load will show us what's actually arriving at renderInvoiceLines.


=== OUTPUT Y ===

# Debugging Invoice Table TypeError

## Root Cause Analysis

The error occurs at line 88 of `invoice-table.tsx` in `renderInvoiceLines()`, where code is calling `.map()` on an undefined value. This is an intermittent issue (3%) that started when the invoice fetch moved to a server component.

**Most likely cause:** The server component fetch is returning undefined or null for the invoice lines array, but the client component doesn't have a guard against it.

## Immediate Debugging Steps

1. **Add a console.log in the server component** — Log the exact return value of the invoice fetch:
   ```typescript
   const invoiceData = await fetchInvoices(...);
   console.log('Invoice data from server:', invoiceData);
   return invoiceData;
   ```
   Check CloudWatch/browser console to see if `invoiceData.lines` is sometimes undefined.

2. **Check the data transformation** — When the server component returns data to the client, is the structure guaranteed? Log what the client component receives:
   ```typescript
   // In InvoiceTable component
   console.log('Received props:', JSON.stringify(props.invoice));
   ```

3. **Add a null check at line 88** — Regardless of the root cause, this is a defensive fix:
   ```typescript
   // Line 88 area - before the .map() call
   if (!props.invoice?.lines || !Array.isArray(props.invoice.lines)) {
     return <div>No invoice lines available</div>;
   }
   return props.invoice.lines.map(line => ...);
   ```

## Why It Started Last Thursday

Moving the fetch to a server component changed the timing and error handling:
- **Before:** Client-side fetch with explicit error handling and fallback state
- **After:** Server component might be throwing, crashing, or returning null/undefined silently

The 3% rate suggests:
- **Race condition** — sometimes the server responds before hydration, sometimes not
- **Intermittent backend issue** — the fetch occasionally fails or times out
- **Edge case in the data** — certain invoice records have missing or malformed `lines` array

## Next Steps (Priority Order)

1. **Verify the server component is not crashing** — Check server logs for errors during invoice fetch
2. **Add error handling in the server component** — Return a sensible default if the fetch fails:
   ```typescript
   const invoiceData = await fetchInvoices(...).catch(err => ({
     lines: [],
     error: err.message
   }));
   ```
3. **Check the database/API** — Does every invoice record have a `lines` field? Is it ever null?
4. **Add Sentry/error tracking** — Instrument the component to catch and report this error with context:
   ```typescript
   try {
     return props.invoice.lines.map(line => ...);
   } catch (err) {
     Sentry.captureException(err, {
       tags: { component: 'InvoiceTable' },
       extra: { invoiceId: props.invoice?.id, linesType: typeof props.invoice?.lines }
     });
     return <ErrorFallback />;
   }
   ```

## Quick Fix (Ship Today)

Add a guard clause at line 87, before `renderInvoiceLines()` is called:

```typescript
// In InvoiceTable component
if (!invoice?.lines) {
  return <LoadingOrErrorState />;
}

return renderInvoiceLines(invoice.lines);
```

This stops the error immediately, then run the root-cause investigation in parallel.


=== OUTPUT Z ===

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

