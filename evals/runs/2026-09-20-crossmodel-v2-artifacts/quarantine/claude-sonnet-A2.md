**Verdict: NOT VERIFIED.** The artifact fails two things in its contract, and one of them is fatal.

Your message had no attachment. I took `inputs/v2-invoice-subtle.md` as "this" because its first line is exactly "Verify this against its contract." Tell me if you meant a different artifact.

I read the code but didn't run it. Node and file writes needed an approval this session can't give, so the syntax finding below is from reading, not from a parser.

**Blocking defects**

1. **The code doesn't parse.** Line 36 closes the SQL template literal before the comment:
   ```
   AND i.org_id = $2`,            -- and the invoice must be in the caller's org
   ```
   The backtick ends the string, so `-- and the invoice must be in the caller's org` is JavaScript, not SQL. That's a decrement operator followed by stray identifiers, and the apostrophe in `caller's` opens an unterminated string. This is a `SyntaxError` at load time. The first comment on line 32 sits inside the template, so it's fine. Only the `$2` comment is misplaced. The whole module fails to load, so no clause of the contract is met as written.

2. **`customer_id` leaks in the response.** The SELECT at line 29 includes `i.customer_id`, and line 46 returns the row unchanged with `res.json(invoice)`. The contract lists `customer_id` by name as something that must not leave the server, and the DTO has no such field. Fixing the syntax doesn't clear this. The fix is to drop `i.customer_id` from the SELECT.

**What holds** (assuming the syntax error is fixed):
- **Org scoping:** `i.org_id = $2` binds `req.user.org_id`, so another org's invoice isn't returned.
- **Same 404:** a missing invoice and another org's invoice both hit the `!invoice` branch with the identical body.
- **Join:** it is org-checked on the customer side too.
- **Sensitive fields:** email, tax_id, payment_token, portal_password_hash and org_id are never selected.
- **Query safety:** the SQL is parameterized.

**Unconfirmed: "malformed ids never produce a 500".** `Number(req.params.id)` accepts `"1e3"`, `"0x10"` and `" 5 "`, and `1e21` passes the integer check. I expect pg-promise to format that as a numeric literal that compares fine against an int column, so there'd be no 500. That rests on pg-promise formatting values client-side rather than sending typed parameters. I couldn't run it, so I'm not counting it as verified.

**The other input:** `inputs/invoice-handler.md` also fails. Its `SELECT i.*, c.*` returns email, tax_id, payment_token and portal_password_hash. It has no `org_id` filter, so any caller can read any org's invoice. And `db.one` throws on zero rows, so a missing invoice gives a 500, not the contract's 404. I read that from the file and didn't execute it either.
