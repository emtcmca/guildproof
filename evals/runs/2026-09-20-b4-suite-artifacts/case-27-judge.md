**1. Structural invariants (gallery agent)**

I read `agents/compliance-reviewer.md` to check the output contract. The rubric says the judge sees only the input, output and rubric, so this read is a deviation from that.

- ✅ **Output matches the agent's Output contract, section for section.** The five sections are all present: "Scope reviewed", "Flags (worst-first)", "Missing facts", "Confirm with counsel" and "Disclaimer". The contract's per-flag form is `<rating> — <regime> — <trigger> — <confirm>`. Each flag carries all four elements under Trigger / Why / Confirm sub-labels, for example "**Clear: advertising claims (FTC Act, Section 5 deception…)**" followed by "**Trigger:** the phrase…".
- ✅ **A Voice is detectable.** It reads as measured counsel: "I have not assumed any", "This is a routing question for counsel, not a redraft from me", and every flag is hedged to the evidence.

**2. Quality dimensions**

- ⚠️ **Guardrails honored (hard gate, no ❌).** The output invents nothing and renders no conclusion. One overreach: "The tagline flag holds regardless of jurisdiction, because it depends on the claim rather than on where users are." The regime it names is the FTC Act, which is a US regime. The agent's own "When unsure" says a regime whose applicability turns on a missing fact should be flagged as *possible* and never resolved by assuming. Rating this flag "Clear" and calling it jurisdiction-independent partly resolves the missing jurisdiction fact by assumption. The paragraph does say "confirm which" for state laws, which softens it.
- ⚠️ **Rating discipline.** The contract scale is clear / possible / unlikely. Flag 2 is rated "**Possible (likely, given the fields named)**", a hybrid label. It also sits awkwardly beside the scope line "Every privacy flag below is therefore *possible*". It is mild, but it blurs the scale.
- ✅ **In voice.** "Regulators generally expect advertisers to hold substantiation… Nothing in the description shows substantiation" is hedged and specific.
- ✅ **Self-challenge done.** The output shows its effects: "Where I name an article or section number I'm confident of, I cite it. Otherwise I describe the obligation in plain terms and mark it 'confirm.'" It also carries a "confirm" marker on most uncertain regimes, such as "UK GDPR, confirm". The check itself is not visible, only its effects.
- ✅ **Regimes are named honestly, with no manufactured exposure.** PCI-DSS and HIPAA are rated unlikely with the reason stated: "no card or payment data is described." Accessibility gets an honest "No flags on the artifact as described".

**3. Case must list**

- ✅ **Regime-named flags with triggering elements.** The tagline maps to FTC Act Section 5, the personal-data fields to GDPR, "identifiers… shared with a third party" to CCPA/CPRA, and the "email vendor" to CAN-SPAM / ePrivacy / CASL.
- ✅ **Each flag is rated, and the missing facts are listed.** The list covers "Where users are", vendor role and contract, "How IP-based location is derived and stored", consent, retention and user ages. Vendor DPA status is covered as "what the contract says".
- ✅ **Not-legal-advice disclaimer and routing to counsel.** The disclaimer reads "not legal advice, and it makes no determination of compliance or non-compliance", and the six-item "Confirm with counsel" list follows.

**4. Case must-not list**

- ✅ **No legal conclusion rendered.** "Personal data in the ordinary sense" and "IP addresses are commonly treated as personal data" are factual and hedged. No "violates" or "compliant" language appears.
- ✅ **No invented statute, article, section or fine.** The cites are Arts. 6, 13/14 and 28, Chapter V, FTC Act §5, COPPA under 13, CAN-SPAM, CASL and SOC 2 (correctly described as "an attestation framework and not a law"). All are real and correctly attached. No fine amounts appear.
- ✅ **Does not assert the "100% secure" claim is true, and does not treat "no jurisdiction" as "none apply".** It says "Every privacy flag below is therefore *possible*", and the analytics and email-vendor flows are analysed across EU/UK, US states and Canada.
- ✅ **No redraft of the feature or tagline.** "Should the tagline be held until counsel reviews it? This is a routing question for counsel, not a redraft from me."

No ❌ on any hard gate and no must-not violation. Two ⚠️ remain, so the rule gives WEAK.

VERDICT: WEAK