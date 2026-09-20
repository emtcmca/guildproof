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
