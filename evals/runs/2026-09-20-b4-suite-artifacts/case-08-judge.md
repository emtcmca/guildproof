## 1. Structural invariants (gallery agent)

I could not see `agents/feature-spec.md`, so I scored the contract against the case's must list, which names all eight sections.

- ✅ **Output contract, section for section.** All eight sections appear in order: "Problem", "Primary user + job", "MVP slice", "Requirements", "Out of scope / later", "Risks & open questions", "Success criteria", "Sharpest objection".
- ✅ **A Voice is detectable.** Examples: "You may be building the wrong thing." and "I'd guess **[A]** the underlying job is…". It reads as a blunt, opinionated spec-writer, not a generic assistant.

No structural hard-gate failure.

## 2. Quality dimensions

- ⚠️ **Guardrails honored (hard gate).** The cut line and the sharpest objection are both stated, but product-fact hygiene leaks.
  - The output opens with a blanket note: "anything about the current product below is an assumption… I've marked these as **[A]**." The marking is then inconsistent.
  - Risk 2 says "I don't know if it has roles, an audit log, or row-level security." Yet Risk 3 states "Nothing caps this today" with no [A] on the claim. The [A] sits only on the following suggestion, "Consider caching shared views…".
  - Unmarked product presuppositions: "a workspace admin who controls whether external sharing is allowed", "workspace-level setting", "Only users with edit rights", "Some connected sources may forbid…", "customers' security teams will ask for domain allowlists, SSO". These assume workspaces, roles, multi-tenancy and B2B customers.
  - The blanket disclaimer mitigates this but does not clear it. The "Nothing caps this today" sentence contradicts the output's own "I don't know" stance.
- ✅ **In voice.** "One forwarded email away from leaking company data" and "one-way door" are direct and persona-consistent.
- ✅ **Self-challenge done.** The Sharpest objection is substantive. It argues that scheduled snapshots deliver most of the value with far less risk, and it names a condition under which the MVP is still right ("only if recipients need live data or interactivity"). It also notes "A dedicated test" for cross-tenant isolation and that screenshotting is not preventable.
- ⚠️ **MVP tightness.** The MVP slice is one feature, but the requirements list is heavy for a first cut:
  - workspace admin toggle
  - viewer list plus revoke
  - a 60-second revocation SLA
  - append-only audit log visible to owners and admins
  - rate limiting per email and per IP
  - first-view notification
  - blocking of RLS-dependent dashboards

  Only the notification is flagged as cuttable ("Cut it first if the slice slips"). The audit log and admin toggle drift toward a permissions platform without being justified as MVP-critical.
- ⚠️ **Success criteria.** Adoption is "a target share of workspaces… Set the number after checking the baseline". That is a placeholder, not a checkable criterion. Displacement has no baseline. The security-gate items are concrete and checkable.

## 3. This case's must list

- ✅ **Full Output contract produced.** All eight sections are present.
- ✅ **Real MVP slice and explicit cut line.** The MVP slice is email-verified, read-only, one dashboard, with expiry and revoke. "This is the cut line" introduces a seven-item "Later" list.
- ✅ **Genuine risks surfaced.** The output covers external auth (one-time code, rate limits), link security and expiry (expiry required, revocation), data exposure ("can only execute the queries behind the widgets…", RLS block, cross-tenant isolation), permissions (edit rights, admin toggle), third-party data terms, and a compliance flag.
- ✅ **Sharpest objection stated.** "You may be building the wrong thing." It frames external sharing as a security surface that may not be the right mechanism, and it gates the build on confirming the recipient need first.

## 4. This case's must-not list

- ✅ **Did not inflate into a full sharing platform.** It is one feature with one slice. Public links, embedding, external accounts, snapshots and per-recipient filtering are explicitly deferred. The requirements list is heavier than ideal (see above), but it stays within one MVP.
- ✅ **Product facts flagged as assumptions, with a leak.** The opening blanket note plus many [A] tags means facts are not presented as known overall. Adversarially, "Nothing caps this today" and the unmarked workspace/admin/edit-rights presuppositions come close to a violation. I held this at ✅ only because of the explicit blanket disclaimer, and I carried the concern into the ⚠️ on guardrails above.

## Verdict rule

There is no ❌ anywhere, but there are ⚠️ marks (product-fact hygiene leak, MVP heaviness, soft adoption criterion). By the rubric this is WEAK.

VERDICT: WEAK