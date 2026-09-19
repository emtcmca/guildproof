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
