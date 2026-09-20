**Verdict: NOT VERIFIED.** The artifact breaks the contract's "nothing else leaves the server" clause, and as pasted it also appears not to parse.

I'm assuming "this" means the contract and artifact in `inputs/v2-invoice-subtle.md`, since your message is that file's first line and only the sentence arrived. If you meant something else, tell me and I'll redo it. I read the code but didn't run it. My attempt to run a syntax check was blocked, so finding 2 is from reading only.

**Findings, most severe first**

1. **`customer_id` leaks.** The SELECT includes `i.customer_id` (line 29), and `res.json(invoice)` (line 45) sends the raw row. The contract lists `customer_id` by name as something that must not leave the server, and the response shape is `InvoiceDTO` plus one extra field. The comment at line 14 says "invoice plus its customer's name", which hides this. No allowlist sits between the query and the response, so any column added to the SELECT later leaks the same way. Fix: drop `i.customer_id` from the SELECT and build the response explicitly from the six DTO fields.

2. **The SQL comment on line 36 appears to sit outside the template literal.** The closing backtick comes right after `$2`, so `-- and the invoice must be in the caller's org` lands in JavaScript. That should be a syntax error, and the apostrophe in "caller's" would start an unterminated string. It may be a transcription slip in the test file. If the real handler has it, the route never loads. The comment on line 34 is inside the template and is fine.

3. **Minor, no contract breach: `Number(req.params.id)` accepts non-canonical forms.** Strings like `"1e3"`, `"0x10"`, `" 12 "` and `"1.0"` all pass as valid ids and resolve to a different invoice than the URL text suggests. None of them produces a 500. `/^\d+$/` plus an upper bound of 2147483647 would be stricter.

**Held, checked by reading**
- Org scoping: `i.org_id = $2` is bound to `req.user.org_id`.
- A missing invoice and another org's invoice both return the same 404 body, because `oneOrNone` returns null for both.
- `email`, `tax_id`, `payment_token`, `portal_password_hash` and `org_id` are not selected, so they can't leak.
- Malformed ids are rejected with a 400 before the query runs.

**Not verified**
- Whether ids above 2^31, such as `"99999999999999999999"`, cause a 500. That depends on how pg-promise formats the value and I couldn't run against a database. I expect a 404, but this is unconfirmed.
- The `due_date` type. pg returns a JS `Date`, so the JSON will be an ISO timestamp rather than a plain date. The contract doesn't say which is expected.

I didn't open the other files in this directory (`out*`, `judge*`, `label-key*`), so nothing here was influenced by earlier arm outputs.

The session hook also asked about registering this directory as a vault project. I skipped that so as not to interrupt the request, so it will ask again next session.
