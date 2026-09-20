# Execution plan: "Export my data as CSV"

## Goal and definition of done

**Goal:** A signed-in user clicks a button on account settings. The app builds an export of their data in the background and emails them a link. The link downloads their CSV.

**Done means all of these hold in production behind a flag:**
- The end-to-end flow works for a real account.
- The export contains only that user's allowlisted data.
- Links expire and files are deleted.
- Failures are visible to the user and to us.
- Rollback is one flag flip.

## Assumptions (I've seen none of your codebase, so all of these are unconfirmed)

- The app has authenticated users with an email address on file.
- It has, or can add, a background job runner, private file storage and a transactional email sender.
- "My data" spans more than one table, so the output may be a zip of CSVs rather than one file.
- I've given no time estimates. Without knowing the stack or data volume they'd be invented.

Task #1 exists to confirm or kill these. If any is false, the graph below changes. Storage or queue infrastructure that doesn't exist yet would add tasks in front of #3.

## Tasks

**#1 Confirm codebase facts and lock five decisions (spike, no feature code)**
- Acceptance: a short written record answers each of these.
  1. Job runner, storage, mail sender and feature-flag mechanism: what exists?
  2. Export scope: an explicit field allowlist per entity, with excluded fields named (password hashes, internal flags, other users' data). Is this a privacy-request (DSAR) fulfillment? If yes, completeness is a requirement, not a nicety.
  3. Format: one CSV or a zip of CSVs.
  4. Link model: a bearer link, or a link to a logged-in download page. I recommend logged-in (see risks). Also the link TTL.
  5. Measured p50/p95/max export size for real accounts.
- Depends on: none

**#2 Export job record, request endpoint and feature flag (dark)**
- Migration adds an `exports` table: user, status (`requested → running → ready | failed | expired`), timestamps, file key. The migration is tested up and down on a staging copy.
- `POST` endpoint is authenticated and returns 202 plus the job. A second request while one is active returns the existing job, so a double-click or retry creates one job. Rate limit per user.
- Flag off means endpoint 404s and nothing is user-visible.
- Acceptance: tests cover 401 for anonymous, 202 for a valid user, the same job returned on duplicate, and the flag-off path. The user can only read their own job (an IDOR test with user B fetching user A's job id).
- Depends on: #1

**#3 Worker produces a real CSV for one entity (profile only), streamed, to private storage**
- Runs off the request path. Writes in a streaming fashion, not a full in-memory build. Escapes CSV correctly. Neutralizes spreadsheet formula injection (cells beginning `=`, `+`, `-`, `@`). Marks the job `ready` or `failed` with a reason. Safe to retry. Logs job id and duration but never row contents or PII.
- Acceptance: for a seeded account, the file matches the DB row exactly. A malicious cell such as `=HYPERLINK(...)` comes out inert. Killing the worker mid-job and retrying yields one file, not two. The file is not publicly readable in storage.
- Depends on: #2

**#4 Download endpoint with expiring link**
- Implements the link model chosen in #1. Expired links return 410. Tampered or unknown tokens return 404 with no information leak. If the link goes to a logged-in page, the user's own session is required.
- Acceptance: the owner downloads within the TTL. After the TTL, the link returns 410. User B cannot download user A's export by any URL. A guessed token fails.
- Depends on: #3

**#5 "Your export is ready" email**
- Sent on the transition to `ready`. Contains the link only, never the data. Sending is idempotent per job: a mail retry or a re-delivered job event doesn't send a second email. A mail failure is recorded and retried without regenerating the export.
- Acceptance: on staging, one ready job produces exactly one email to the account address, and the link in it works. A forced send failure retries and still ends at one delivered email. The `failed` path either emails a failure notice or deliberately doesn't (decided in #1, tested here).
- Depends on: #3, #4 (the link shape). The template can be drafted in parallel against a stub link.

**#6 Account-settings button and states**
- Built against #2's API contract. States: idle, requesting, "in progress, we'll email you", active-job-exists (button disabled), failed with retry, rate-limited. Keyboard-operable, with a labeled control and a status message announced to screen readers. Hidden when the flag is off.
- Acceptance: each state is renderable and tested. Tab and Enter work with no mouse. A double-click sends one request. The failure state names what to do next.
- Depends on: #2 (mockable, so it runs in parallel with #3–#5)

**#7 End-to-end walking skeleton on staging (milestone)**
- Acceptance: with the flag on for a test account, click → email arrives → link downloads a correct profile CSV, observed by a person. Paste the evidence (email, file), not a green log line.
- Depends on: #4, #5, #6

**#8 Widen to remaining entities (one sub-task per entity group from the #1 allowlist: 8a, 8b, …)**
- Each sub-task reuses #3's pattern and ships independently. Packaging into a zip happens here if #1 chose that.
- Acceptance, per entity: for a seeded multi-entity account, row counts equal DB counts. Only allowlisted columns appear, and excluded fields are absent. Zero rows belonging to another user, verified with a second seeded account.
- Depends on: #3 (pattern), #1 (allowlist)

**#9 Retention and cleanup**
- A scheduled sweep, plus a storage lifecycle rule as a backstop, deletes files past TTL and marks jobs `expired`.
- Acceptance: a file aged past TTL is gone from storage. Its link returns 410. Deleting a user's account also removes their export files (or the decision to retain is documented).
- Depends on: #3, #4

**#10 Scale check**
- Acceptance: a synthetic account at the p95/max size from #1 exports within the job timeout, with memory staying flat (streaming holds). The primary database isn't visibly stressed (batched reads or a replica). A concurrent-exports test confirms the queue doesn't starve normal jobs.
- Depends on: #8

**#11 Independent verification pass (by someone other than the builder)**
- Attempt to refute: IDOR on job and download, link guessing, formula injection across every entity's text fields, PII in logs, email sent twice, expired-link behavior, flag-off leakage.
- Acceptance: a written verdict listing what was tried and what held. Any blocking gap is fixed and re-tested before #12.
- Depends on: #7, #8, #9

**#12 Observability and staged rollout**
- Metrics: requested, succeeded, failed, duration, email failures. An alert on failure rate. A short runbook covering a stuck job and a mail outage. Rollout: internal accounts, then a small percentage, then everyone.
- Acceptance: a dogfood export from a real internal account succeeds. Forcing a failure trips the alert. Turning the flag off hides the button and blocks the endpoint (rollback rehearsed, not assumed).
- Depends on: #10, #11

## Critical path

**#1 → #2 → #3 → #4 → #5 → #7 → #11 → #12**

Everything downstream waits on #3, the first real worker. A co-critical branch runs **#3 → #8 → #10 → #11**. Which branch is longer depends on how many entities #1 puts in the allowlist, and I can't know that yet. If the allowlist is large, the #8 branch dominates and should get the most people.

## Parallelizable

- **#6** (UI) runs alongside #3–#5, as soon as #2's API contract exists.
- After #3, **#4**, **#8** and the drafting of **#5**'s template can run concurrently.
- **#9** can run beside #8 once #4 is done.
- The **#8** sub-tasks are independent of each other.
- **#10** and **#11** overlap once #8 lands, as long as the fixes from #11 are re-tested afterward.

## Risks and decision points

**Sharpest objection: do you need async plus email at all?**
- Async, email and expiring links is real infrastructure. If #1 shows most accounts export in a couple of seconds, a synchronous streaming download from the button is a much smaller build.
- You asked for email, so I've planned it. But #1's size measurement is the cheap test of that premise, and I'd look at it before committing to #2–#5.
- Email delivery itself has a cost. Emails land in spam or get delayed, and users then ask where their export is. The UI states in #6 are the mitigation. Showing past exports on the settings page is a plausible follow-up, deliberately cut from this plan.

**Decisions that gate progress (all in #1)**
- **Link model.** Email isn't a secure channel. A bearer link in an inbox is a data-exfiltration path for anyone with mailbox access. I recommend the link lead to a logged-in page, which then issues a short-lived storage URL. Only the app's owner can make this call. It changes #4 and #5.
- **Re-authentication.** Should the request require a fresh password or step-up check, and should we send a "an export was requested" alert? A hijacked session could otherwise export everything with one click.
- **Scope and compliance.** If this backs a legal data-access request (GDPR/CCPA-style), the allowlist must be complete and deadlines may apply. I've flagged this as a question and made no legal assumption. Route it to whoever owns compliance.
- **Failure notice.** Whether a failed export sends an email, or only shows in the UI.

**Unconfirmed infrastructure**
- I assumed a job runner, private storage and a mail sender exist. If any is missing, add a task in front of #3 for it. Each is a real dependency, not a footnote.

**Technical risks**
- **Memory and DB load.** Building the file in memory, or querying a big account against the primary, will fail only at scale, which demo data won't show. #3 must stream by design, and #10 exists to prove it.
- **Formula injection.** It's built in at #3, so no later task can break it silently. #11 re-attacks it on every entity.
- **Partial data.** The export can silently omit a table someone forgot. #8's row-count-versus-DB check is the guard. There's no other way to notice an omission.
- **Retention.** Files that never expire are a standing privacy liability. That's why #9 is in scope, not a follow-up.

**Cut line, if scope must shrink**
Ship #1–#7, #9, #11 and #12 with the profile entity plus the two or three highest-value entities from #8. Defer the rest of the entities, and #10 only if #1's measurement shows small data. Do not defer #9 or #11.