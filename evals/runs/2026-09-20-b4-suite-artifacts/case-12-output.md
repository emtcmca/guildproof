# SOP: Onboarding a New HOA Client's Governing Documents

**Version:** DRAFT v0.1 · **Owner:** [SOP owner, confirm] · **Last reviewed:** [date]

I inferred the following because your request didn't say. Each item is marked ⚑ and collected under Confirm-these.
- "Our system" is BoardPath's document ingestion (OCR, auto-classification, authority-tier hierarchy, amendment chaining).
- The client is a community association whose documents you receive from a board member or manager.

## 1. Purpose & trigger

**Purpose:** Get every governing document for a new association into the system correctly. That means complete, readable, classified, in the right authority order, with every amendment linked to its parent. It also means proving the system answers questions from those documents accurately before the client uses it. A missing amendment or a wrongly ranked document produces confident wrong answers, so this SOP is built to catch both.

**Trigger:** The client agreement is signed ⚑ and the account owner hands you the new association's name and contact.

**Done-state (all must be true):**
1. Every document on the inventory sheet is loaded and passed the quality check.
2. The amendment chain shows zero orphans, or each orphan is logged as a known missing parent.
3. The five-question retrieval test passed.
4. A reviewer other than you signed off.
5. The client received the "what's loaded / what's missing" message.
6. Every missing document is in the tracker with a follow-up date.

## 2. Roles

| Role | Owns | Placeholder name ⚑ |
|---|---|---|
| **Onboarding Operator (you)** | Steps 1–21 except sign-off | [name] |
| **Reviewer** | Picks the retrieval test questions, checks the results, signs off (Steps 16–18). Must not be the Operator. | [name] |
| **Account Owner** | Relationship with the client. Sends document requests and follow-ups. Decides what to do when the client can't produce a document. | [name] |
| **System Admin / Engineer** | Fixes stuck ingestions, failed extractions, and wrong-tier rankings. | [name] |

*If one person holds every role, do the Step 16–18 review at least one business day after Steps 1–15, from the inventory sheet and not from memory. Record it as "self-reviewed."*

## 3. Steps

### Phase A: Intake

1. **Create the community record** in [system name ⚑]. Enter:
   - the exact legal name of the association, copied from the Articles or Declaration (not the name people call it)
   - state, county, and type (HOA or condo)
   - the client contact
   - **Verify:** the record appears in the community list and the legal name matches page 1 of the Declaration once you have it.

2. **Create the client's document folder** at [path ⚑] with three subfolders: `original`, `working`, `inventory`.
   - Working name pattern: `association-name/doc-type-YYYY-MM-DD.pdf`. It is lowercase, hyphenated, and dated with the document's own date.
   - **Verify:** open the folder and confirm all three subfolders exist.

3. **Send the client the document request** (Account Owner sends it) listing exactly these items:
   - Recorded Declaration / CC&Rs
   - Every recorded amendment or supplement to the Declaration
   - Articles of Incorporation
   - Bylaws and every amendment
   - Rules & Regulations
   - Board-adopted policies (collections, fines, architectural guidelines)
   - Board resolutions that changed a rule
   - Ask for the recorded, county-stamped copy where one exists. Drafts and Word files are not acceptable substitutes for recorded documents.
   - **Verify:** the request is sent and logged in [tracker ⚑] with today's date.

4. **Set the follow-up date** in [tracker ⚑] for [3 business days ⚑] after the request.
   - **Verify:** the tracker shows the item with a date.

5. **Save everything the client sends** into `original` on the day it arrives. This includes anything sent by email or text.
   - **Verify:** the file count in `original` equals the number of attachments you received.
   - Never edit or rename files in `original`.

### Phase B: Inventory and pre-check

6. **Copy each file from `original` into `working`.** Do all further work on the copies.
   - **Verify:** both folders show the same file count.

7. **Open each file in `working`** and confirm it opens, is not password-protected, and has readable pages from first to last. Compare the PDF page count with any "Page x of y" footer.
   - **Verify:** you have paged through each file. Anything that fails goes to Exceptions E1.

8. **Split any combined PDF** (for example a Declaration with five amendments bound together) into one file per document. Keep the combined file untouched in `original`.
   - **Verify:** each split file has exactly one document date and one title.

9. **Rename each working file** to the pattern in Step 2. Use the date on the document itself, not today's date.
   - **Verify:** no two files share a name, and every name follows the pattern.

10. **Confirm every file belongs to this association.** On each document, check that the association's legal name and the recording number on page 1 match the community record.
    - **Verify:** if any file names a different association, go to E9.

11. **Build the inventory sheet** at `inventory/inventory.xlsx` ⚑ with one row per document. Columns: filename, document type, document date, recording info, page count, text or scan, who supplied it, parent document (for amendments), status.
    - **Verify:** the row count equals the file count in `working`.

12. **Fill in the parent column.** For each amendment, write which document it amends and its number ("Amendment No. 3 to the Declaration"). Then look for gaps: an Amendment No. 3 with no No. 2, or an amendment that cites a document you don't hold.
    - **Verify:** every amendment row has a parent, or the word "MISSING." Every MISSING row goes to E5.

13. **Assign each document a tier** on the inventory sheet using this order, highest first: state statute, Declaration/CC&Rs, Bylaws, Rules/policies/board motions, other. Amendments are not a separate tier. They take their parent's tier.
    - **Verify:** no amendment row carries a tier different from its parent's.

14. **Check that the state statute is already loaded** in [system location ⚑] for this association's state.
    - **Verify:** the statute is present. If not, go to E12.

### Phase C: Ingestion

15. **Upload the files from `working`, parents before children.** The order is Declaration, then its amendments, then Bylaws, then their amendments, then Articles, then Rules and policies, then resolutions. Upload to [upload location ⚑].
    - **Verify:** the system's document list for this community shows one entry per file, and the count equals your inventory count.

16. **Wait for each document's status** to reach [processed status ⚑]. Check every [5 minutes ⚑] up to [30 minutes ⚑].
    - **Verify:** no document is left in a pending or failed state. Anything that is goes to E3.

17. **Read the extraction quality score** for each document at [where shown ⚑]. Write it in the inventory sheet.
    - **Verify:** every score meets the system's gate. The current gate is 0.6 per project notes ⚑. Anything below goes to E2. Do not change the gate.

18. **Spot-check the extracted text of every document** against the source. Look at the first page, one middle page containing a numbered list or table, and the last page. Confirm the section numbers and headings match the source (for example "Article VII, Section 7.3").
    - **Verify:** the text on all three pages matches the source. If numbering is lost or scrambled, go to E2.

19. **Check the document type the system assigned** to each document against your inventory sheet. Correct any mismatch in [where ⚑].
    - **Verify:** the system's type matches the inventory for every row.

20. **Link each amendment to its parent** in the system, using the parent column from Step 12. Do not link to a guess (see E5).
    - **Verify:** the amendment chain view shows each amendment under the right parent, and the Warning Center (or equivalent) shows zero orphan warnings for this community, apart from the MISSING rows you logged.

### Phase D: Retrieval test and sign-off

21. **Reviewer writes five test questions** from the source documents, with the correct answer and section noted for each. The five must be:
    1. a Declaration question
    2. a Bylaws question
    3. a Rules question
    4. a question whose answer was changed by an amendment (the system must give the amended answer and cite the amendment)
    5. a question the documents do not answer

    - **Verify:** the answer key is saved in `inventory/test-key.txt` before anyone runs the questions.

22. **Operator runs each question** in the system and pastes the answer and the cited section into the answer key file.
    - **Verify:** all five have a recorded answer.

23. **Reviewer grades each question.** Pass means the right answer and the right section citation.
    - Question 4 passes only if the amended text is used.
    - Question 5 passes only if the system says it cannot find the answer, or returns low confidence. A confident answer is a fail. Go to E7.
    - **Verify:** the reviewer marks each question pass or fail. Any fail goes to E6.

24. **Reviewer signs off** in `inventory/inventory.xlsx` (name, date), confirming the document count, the chain, the quality scores, and the test result.
    - **Verify:** the sign-off is present and the reviewer's name differs from the Operator's (or "self-reviewed" is written, per Roles).

25. **Set the community status to ready** and grant the client's users access in [where ⚑].
    - **Verify:** log in as, or view the account as, a client user and confirm the community and its documents appear. Confirm the client can see only their own association.

### Phase E: Close-out

26. **Send the client the completion message** (Account Owner sends it) using [template ⚑]. It lists:
    - each document loaded, with its date
    - each document still missing
    - the plain statement that answers reflect only the documents loaded

    - **Verify:** the message is sent and a copy is saved in `inventory`.

27. **Log every missing document** in [tracker ⚑] with a follow-up date and the owner.
    - **Verify:** each MISSING row on the inventory sheet has a matching tracker entry.

28. **Record the close** by writing the completion date and your name on the inventory sheet.
    - **Verify:** the inventory sheet's status column reads "complete" for every loaded document.

## 4. Exceptions

**E1. File won't open, is corrupt, or is password-protected.** Do not try to crack it. Ask the client for a new copy and log the request. Continue with the other files.

**E2. Quality score below the gate, or numbering scrambled in extraction.**
- Ask the client for a cleaner scan ([300 dpi or better ⚑], flat pages, no shadows), or a copy from the county recorder.
- Re-upload once.
- If it still fails, stop and go to E3. Do not retype text into the system by hand. Do not lower the gate.

**E3. Ingestion stuck or failed.**
- Wait the full timeout in Step 16.
- Retry the upload once.
- If it fails again, send the System Admin the document name, the time, and the error text copied exactly. Leave the rest of the process paused for that document.

**E4. Client can't find recorded documents.** Account Owner decides:
- (a) The client orders copies from the county recorder [fee/turnaround: ask county].
- (b) You load what exists and mark the gaps.
- Minimum to mark the community "ready": [Declaration + Bylaws ⚑]. Below that minimum, do not go past Step 24.

**E5. Amendment references a parent you don't have.** Load the amendment and leave it unlinked. Keep the orphan warning showing. Set MISSING in the inventory, tell the Account Owner, and log the request (Step 27). Never link it to the nearest-looking document.

**E6. Retrieval test fails.**
- If the answer used original text where an amendment applies, check the chain link first (Step 20).
- If the citation is wrong, check the extraction (Step 18).
- Fix, then rerun all five questions, not only the failed one. If you can't find the cause in one pass, escalate to the System Admin. Do not sign off.

**E7. The unanswerable question gets a confident answer.** This is a blocker. Do not set the community to ready. Send the System Admin the question, the answer, and the confidence shown.

**E8. Restated documents ("Amended and Restated Declaration").** The restated version becomes the parent for later amendments. Load the older versions too, for history, and mark them superseded [if the system supports it ⚑]. Note it in the inventory.

**E9. A file belongs to a different association.** Remove it from this community's folder and from the system immediately if it was uploaded. Tell the Account Owner and log it. Different associations often have near-identical names, so the recording number is the check.

**E10. Two conflicting versions of the same document.** Do not pick one. Check the recording stamp and date. The recorded version wins. Ask the client which is current, and keep the other in `original` only.

**E11. Client sends things that aren't governing documents** (minutes, financials, owner rosters, insurance). Do not upload them here. Tell the Account Owner they belong to [separate process ⚑]. Rosters and any page listing owner names or personal data must not go into the governing-documents set.

**E12. State statute not loaded.** Stop before Step 15 for the statute tier. Escalate to the System Admin. Don't mark ready. Statute is the top tier, and answers without it can be wrong in exactly the ways that matter.

**E13. Rules appear to contradict the Declaration.** That is not yours to resolve. Load both as-is. The system ranks by tier. Tell the Account Owner in one line naming both sections.

**E14. Client adds or replaces a document after the community is ready.** Run Steps 6–20 for the new document only. Then rerun all five test questions and get a fresh sign-off.

**E15. You're out mid-process.** The inventory sheet is the handoff. Update its status column before you leave so the next person knows the last completed step.

## 5. Confirm-these

**Assumptions about scope**
- ⚑ "Our system" = BoardPath's ingestion. If it's the P2P file-tree process (`Clients\[Community]\00-Governing-Docs`), Phases C–D change and Phases A–B still apply.
- ⚑ Documents come from the client. If you pull them from county records yourself, add a Step 3 alternative.

**Tools and locations to fill in**
- System name, upload location, where the quality score shows, the "processed" status wording, where to correct a document type, and where to link amendments.
- The client folder path and the inventory sheet location and format.
- The tracker used for follow-ups and missing documents.
- The client completion-message template.

**Thresholds I assumed or carried over**
- Extraction quality gate of 0.6, taken from project notes. Confirm it's still current. Never quote it to a client as a guarantee.
- 3-business-day follow-up, 5-minute status checks, 30-minute timeout, and 300 dpi rescan request. All are placeholders.
- The minimum document set for "ready" (I proposed Declaration + Bylaws).
- Five test questions is my number. Set the one you want.

**People**
- Names for all four roles, and who can serve as Reviewer when the team is one person.

**Product behavior I couldn't verify**
- Whether the system marks a document as superseded (E8).
- Whether the state statute is preloaded per state or per community (Step 14).
- Whether the Warning Center is the orphan-warning view (Step 20).

**Stall points I closed in review:** the "which document is the parent" guess (Step 12 and E5), the confident-wrong-answer case (Step 23 and E7), the wrong-association upload (Step 10 and E9), and the one-person-team sign-off problem (Roles).