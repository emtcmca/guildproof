# Feature spec: external dashboard sharing

**Note on inputs:** The request is one sentence, so anything about the current product below is an assumption to confirm. I've marked these as **[A]**.

## Problem
People who build dashboards can't show them to clients, partners, or advisors outside the company without screenshotting, exporting, or buying those people a seat. **[A]** That workaround is the real pain. "Sharing" is only one possible fix.

## Primary user + job
- **Who:** the dashboard owner (an employee who can edit the dashboard), plus a workspace admin who controls whether external sharing is allowed at all.
- **The one job:** let a specific outside person see one dashboard, read-only, without giving them an account. The owner can cut off access later.

## MVP slice
The owner clicks **Share externally** on one dashboard and enters one or more email addresses. Each recipient gets a link. They open it, verify with a one-time code sent to that same email, and view a read-only live copy of that one dashboard. Access expires, and the owner can revoke it at any time.

I chose email-verified invites over "anyone with the link." A bare link is faster to build, but it is one forwarded email away from leaking company data. The one-time code is the smallest control that ties access to a named person.

## Requirements
**Sharing flow**
- Only users with edit rights on a dashboard can share it externally.
- A workspace-level setting controls external sharing. It is **off by default**, and only admins can change it.
- The owner enters recipient emails and an expiry. Expiry is required. Default is 30 days and the maximum is 90 days. **[A]** Both numbers are proposed.
- The owner can see the list of active external viewers and revoke any of them.

**Recipient experience**
- The recipient opens the link, enters the one-time code emailed to the invited address, and sees the dashboard. No account creation.
- The view is read-only. There is no edit, no export, no download of underlying data, no drill-through to other dashboards or data sources, and no ad-hoc queries.
- Filters and parameters are fixed to the saved state.
- Expired, revoked, and wrong-code states each have a plain-language screen.

**Data exposure**
- An external session can only execute the queries behind the widgets on the shared dashboard. It cannot reach any other endpoint or resource.
- Revocation takes effect on the next request, and no later than 60 seconds. **[A]** The 60 seconds is a proposed target.
- Dashboards that depend on the viewer's identity (row-level security or per-user filters) cannot be shared externally in the MVP. Block them with a clear message.

**Safety and audit**
- Rate-limit code requests and code attempts per email and per IP.
- Keep an append-only log of who shared what, with whom, when it was viewed, and when it was revoked or expired. The owner and admins can see it.
- Email the owner when a recipient first views the dashboard. **[A]** This is optional and cheap. Cut it first if the slice slips.

## Out of scope / later
This is the cut line. The request bundles several features, and this spec covers only the first.
- **Later:** external users with real accounts, comments, or edit rights.
- **Later:** public "anyone with the link" and publish-to-web.
- **Later:** embedding in other sites or iframes, and white-labeling.
- **Later:** scheduled or emailed snapshots and PDFs. See the objection below, because this may deserve to go *first*.
- **Later:** per-recipient data filtering, and sharing a whole workspace or folder.
- **Later:** domain allowlists, watermarking, and IP restrictions.
- **Later:** downloads and CSV export for external viewers.

## Risks & open questions
1. **What data do dashboards contain?** If they hold PII, financial, or customer data, this feature may trigger contractual or regulatory obligations. I can't name a regime from here, so get the compliance-reviewer's read before build.
2. **What is the permission model today?** I don't know if it has roles, an audit log, or row-level security. If not, the safety requirements grow, and the size of the work depends on this more than on the UI.
3. **Who pays for the load?** External viewers run live queries against your data sources. Nothing caps this today. **[A]** Consider caching shared views, or shipping snapshots first.
4. **Third-party data terms.** Some connected sources may forbid showing their data to outsiders. Confirm before launch.
5. **Multi-tenant isolation.** A bug that lets an external session read across tenants is the worst failure mode here, so it needs a dedicated test.
6. **Forwarding and screenshots.** The one-time code stops casual forwarding. It does not stop a recipient from screenshotting. Say so in the UI and the docs rather than implying otherwise.
7. **Never confirmed with users:** whether recipients need *live* data or a point-in-time view. This changes the architecture.

## Success criteria
No baselines were given, so these are proposals to set before build.
- **Security gate (binary, ships or doesn't):**
  - An external session cannot reach any resource other than the shared dashboard's own widgets, verified by test.
  - A revoked or expired link returns no data.
  - Repeated wrong codes trigger the rate limit.
- **Function:** A recipient goes from invite email to a rendered dashboard in under two minutes, without help.
- **Adoption:** Within 30 days of release, a target share of workspaces with external sharing enabled have shared at least one dashboard. Set the number after checking the baseline for "how often users export or screenshot today."
- **Displacement:** Screenshot, export, and "add my client as a seat" requests drop. This needs a support-ticket or usage baseline first, and if none exists, that is a finding in itself.
- **Trust:** Zero reported incidents of unintended exposure in the first 90 days, with the audit log able to answer "who saw what" for any incident.

## Sharpest objection
**You may be building the wrong thing.** "Share with people outside the company" is a mechanism, and I'd guess **[A]** the underlying job is "send my client an update on a schedule." A scheduled snapshot email or PDF delivers most of that value with a fraction of the risk. It needs no external auth surface, no live-query load, no revocation problem, and no cross-tenant exposure path.

Live external access is also a one-way door. Once it exists, customers' security teams will ask for domain allowlists, SSO, and audit exports, and the feature will keep growing.

If a few user conversations show that recipients mainly want a point-in-time view, build snapshot sharing first. Live email-verified sharing above is the right slice only if recipients need live data or interactivity. Confirm that before committing engineering time.