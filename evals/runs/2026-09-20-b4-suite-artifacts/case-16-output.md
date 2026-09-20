# Security review: password-reset flow

**Basis:** the four-line description only. No code, middleware, or auth model was provided. Anything I can't see is treated as absent and listed under Confirm-these. Your statement that "no expiry is mentioned" is treated as unverified. It means either no expiry exists or none was described.

## Attack surface

- **Untrusted inputs:** `token` and `password`, both from the query string of a `GET`. Anyone who can produce a URL controls them.
- **Sink:** the account's stored credential. Whoever supplies a token accepted by this endpoint takes over the account.
- **Trust boundary crossed:** the new password and the reset token both travel in the URL. URLs are recorded by browsers, servers, proxies, CDNs, WAFs, analytics, and email-security scanners, none of which are meant to hold secrets.
- **Implied side channel:** the reset email carries a link containing the token, so the mailbox is part of the trust boundary.

## Findings (worst-first)

❌ **Critical: new password sent in the query string of a GET**
- **Vector:** `GET /reset?token=…&password=…`. The plaintext password is written to web-server and reverse-proxy access logs, CDN and WAF logs, browser history, and any APM or analytics capture of request URLs. It is also sent in `Referer` to any third-party resource the response page loads, unless `Referrer-Policy` is set. Nothing here requires a skilled attacker.
- **Impact:** every reset puts a user's chosen plaintext password, often reused elsewhere, into systems with much broader read access than the user database. This happens on every use, not only under attack. Anyone with log access, such as an ops engineer, a log vendor, or a breach of the log store, gets working credentials.
- **Fix:** submit the new password only in a `POST` body over TLS. Exclude the body from logging. Never accept `password` as a query parameter. Return `Cache-Control: no-store` and `Referrer-Policy: no-referrer` on the reset pages.

❌ **Critical: no stated expiry, and single-use not stated**
- **Vector:** a token that never expires stays valid in the mailbox, browser history, forwarded mail, backups, and, per the finding above, server logs. Single-use is also not mentioned, so a token that has already worked may work again.
- **Impact:** a leaked or old token is a permanent password-reset credential. Combined with the logging above, log access leads to indefinite account takeover, even after the legitimate user has already reset. I'm assuming no expiry exists in unshown code, since you said none is mentioned.
- **Fix:** enforce a short server-side TTL, typically 15–60 minutes, checked at redemption time. Invalidate the token on first successful use. Invalidate all earlier outstanding tokens when a new reset is requested. Invalidate them also when the password changes by any other route.

❌ **High: token entropy and storage unspecified ("generated at request time")**
- **Vector:** this phrase doesn't say how the token is made. If it is derived from a timestamp, user ID, email hash, sequential counter, or a non-cryptographic RNG, it can be predicted or enumerated. If it is stored in plaintext, a database read (SQL injection, backup leak, insider) yields a working takeover token for every pending reset.
- **Impact:** account takeover without mailbox access if the token is predictable.
- **Fix:** generate at least 128 bits from a CSPRNG. Store only a hash (SHA-256 is adequate for a high-entropy random token) plus the account ID and expiry, and look it up by hash.

⚠️ **High: state-changing operation on GET**
- **Vector:** a credential change on `GET` is triggered by anything that fetches a URL. That includes link prefetchers, corporate email scanners such as Safe Links–style rewriters, chat unfurlers, and browser preloaders, which fetch links in reset emails. It can also be triggered by `<img>`, `<a>`, or redirects. The URL is also cacheable and replayable from history.
- **Impact:** at best the token is consumed by a scanner and the user's reset fails. At worst a scanner or crawler replays a URL containing both token and password. Any leaked full URL is a one-click, embeddable takeover. It also gives no CSRF or intent check on the operation.
- **Fix:** the emailed link should only open a page (`GET`, no side effects). The change should happen on a `POST` with the token in the body or a hidden field. Consider a per-form CSRF token.

⚠️ **Medium: no visible rate limiting or attempt controls on redemption**
- **Vector:** an unauthenticated endpoint that accepts token guesses. This is theoretical with 128-bit random tokens, but real if tokens are short or numeric, which the description doesn't rule out.
- **Impact:** token brute-force. Separately, the reset-request endpoint is a candidate for email bombing.
- **Fix:** per-IP and per-account throttling on both redemption and request. Uniform errors for invalid, expired, and used tokens.

⚠️ **Medium: silent password corruption from URL encoding, and no stated password validation**
- **Vector:** characters such as `&`, `#`, `+`, and `%` in a password will truncate or mangle the value unless it is correctly percent-encoded. URL-length limits can truncate long passphrases.
- **Impact:** the user sets a different password than they typed, possibly a truncated weak one, and is locked out. The description also mentions no length, complexity, or breached-password checks, and no confirmation field.
- **Fix:** a body-based `POST` removes the encoding problem. Apply the same password policy as registration, server-side.

⚠️ **Medium: post-reset session and MFA handling not described**
- **Vector:** a reset that doesn't kill existing sessions leaves an attacker's stolen session or refresh token valid.
- **Impact:** the reset doesn't evict a prior compromise. If MFA exists and reset bypasses it, reset becomes the weakest path into the account.
- **Fix:** revoke all sessions and refresh tokens on reset. Require MFA or an equivalent second step where enrolled. Send a "your password was changed" notice to the account email.

## Highest-severity issue

The new password is sent as a query parameter on a GET. Every reset writes the user's plaintext credential into logs, history, and Referer headers, and the token that authorizes it may never expire.

## Confirm-these

Each is a control that may exist in unshown code. I treat them as absent until shown.

1. **Token TTL and single-use enforcement:** where and how they are checked, and whether the token is invalidated on use.
2. **Token generation:** which RNG, how many bits, and whether it is stored hashed.
3. **Reset-link construction:** whether the base URL comes from configuration or from the `Host` / `X-Forwarded-Host` header. If the header is trusted, an attacker can request a reset for a victim and have the victim's email carry a link to an attacker-controlled host, which leaks the token on click.
4. **Log and monitoring redaction:** whether any layer (proxy, CDN, APM, error tracker) already strips `password` and `token` query parameters. Even if so, past logs may already hold real passwords and need purging.
5. **Reset-request behavior:** whether the endpoint responds identically for existing and non-existing accounts (enumeration), and whether it is rate-limited.
6. **Transport:** HTTPS-only with HSTS, with no plaintext-HTTP redirect that would leak the URL.
7. **Password storage:** hashed with a modern password hash (argon2id, bcrypt, scrypt) on write.
8. **MFA interaction:** whether a reset skips MFA for accounts that have it.
9. **Other tokens:** whether a new request revokes earlier outstanding tokens.

*Artifact note:* the material contained no text addressed to the reviewer, so nothing needed flagging as an embedded directive.