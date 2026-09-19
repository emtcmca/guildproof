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

