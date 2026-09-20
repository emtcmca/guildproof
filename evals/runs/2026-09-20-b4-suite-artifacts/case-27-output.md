# Compliance flag list: user data collection, vendor sharing, and the "100% secure" tagline

## Scope reviewed

- **Assessed:**
  - Collection of email, full name, and IP-derived approximate location.
  - Storage of that data in an analytics DB.
  - Sharing of it with a third-party email vendor.
  - The proposed marketing tagline "the only 100% secure way to manage your data."
- **Jurisdictions and populations:** none were supplied, and I have not assumed any. Every privacy flag below is therefore *possible* until the deciding facts are known. The tagline flag holds regardless of jurisdiction, because it depends on the claim rather than on where users are.
- **Regimes walked:** privacy (GDPR, CCPA/CPRA, other US state laws), email marketing, advertising (FTC), security controls (SOC 2), payments (PCI-DSS), health (HIPAA), children's privacy, accessibility.
- **Verification:** the description is the only input, and none of it is verified. Where I name an article or section number I'm confident of, I cite it. Otherwise I describe the obligation in plain terms and mark it "confirm."

## Flags (worst-first)

1. **Clear: advertising claims (FTC Act, Section 5 deception; state unfair/deceptive-practices laws, confirm which).**
   - **Trigger:** the phrase "the only 100% secure way to manage your data."
   - **Why:** it is an absolute security claim ("100%") combined with an exclusivity claim ("the only"). Both are objective, verifiable claims, and regulators generally expect advertisers to hold substantiation for them before making them. Nothing in the description shows substantiation. An absolute security claim also creates a comparison against any later incident, breach, or vendor-side exposure.
   - **Interaction with the data flow:** the claim is about how the product "manages your data," while the data goes to a third-party vendor and an analytics store. A claim that omits or contradicts that sharing raises a separate question of whether the overall impression is misleading.
   - **Confirm:**
     - Is there documented substantiation for each element of the claim ("100%," "only," "secure")?
     - Does the claim match what the privacy notice and vendor terms say?
     - Should the tagline be held until counsel reviews it? This is a routing question for counsel, not a redraft from me.

2. **Possible (likely, given the fields named): privacy, EU/UK, GDPR (and UK GDPR, confirm).**
   - **Trigger:** name, email, and IP-derived location are personal data in the ordinary sense, and IP addresses are commonly treated as personal data. Confirm whether the raw IP is retained, or only the derived location.
   - **Sub-flags, all turning on whether any EU/UK residents are in the user base:**
     - **Lawful basis (Art. 6):** none is stated for the analytics use or for the vendor sharing.
     - **Transparency (Arts. 13/14):** what users are told at collection is not described.
     - **Processor arrangement (Art. 28):** does the email vendor act as a processor under a written contract, or as an independent controller?
     - **International transfers (Chapter V):** applicable if the vendor or its sub-processors sit outside the EEA/UK.
     - **Purpose and retention:** an "analytics DB" holding identifying fields raises purpose-limitation and retention questions. Analytics use and email marketing may be distinct purposes.
   - **Confirm:** presence of EU/UK users, lawful basis per purpose, vendor role and contract, transfer mechanism, retention period.

3. **Possible: privacy, US, CCPA/CPRA and other state comprehensive privacy laws (confirm which states and whether thresholds are met).**
   - **Trigger:** identifiers (name, email, IP-derived location) shared with a third party.
   - **Sub-flags:**
     - **"Sale" or "sharing":** whether the vendor arrangement is a service-provider/processor relationship or a disclosure that counts as a "sale" or "share." That turns on the contract terms and on whether the vendor may use the data for its own purposes.
     - **Notice at collection and privacy policy disclosures:** confirm the disclosure content required.
     - **Opt-out mechanics:** required if the arrangement counts as a sale or share.
     - **Location precision:** "approximate" IP-based location may fall below any "precise geolocation" sensitive-data category. Whether it does depends on the granularity and on each statute's definition. Confirm.
   - **Confirm:** applicability thresholds, vendor contract terms, granularity of stored location, current privacy policy text.

4. **Possible: email marketing rules (CAN-SPAM in the US; ePrivacy-type consent rules in the EU/UK; CASL in Canada; confirm which apply).**
   - **Trigger:** sharing email addresses with an "email vendor" implies commercial or marketing messages. The description doesn't say whether these are marketing or transactional, or how consent was captured.
   - **Confirm:**
     - Message type (marketing vs. transactional).
     - Consent or opt-out mechanism per jurisdiction.
     - Unsubscribe handling, and whether suppression lists are synchronized to the vendor.

5. **Possible: security controls and representations (SOC 2, GDPR security-of-processing obligations, state "reasonable security" duties; confirm).**
   - **Trigger:** the tagline makes a security representation, and the data flow adds a third party to the security perimeter.
   - **Why it matters:** SOC 2 is an attestation framework and not a law. Customers may ask for it, and the tagline invites scrutiny of exactly those controls. Vendor due diligence is also relevant, because the claim is only as strong as the vendor's controls.
   - **Confirm:** existing security attestations, vendor security review status, encryption and access controls on the analytics DB, breach-notification obligations that would apply if an incident occurred.

6. **Unlikely-but-note: children's privacy (COPPA in the US; age-related provisions in GDPR, confirm).**
   - **Trigger:** none in the description. Applicability turns entirely on whether users under 13 (or the local age threshold) can sign up.
   - **Confirm:** intended and actual user age range.

7. **Unlikely-but-note: payments (PCI-DSS) and health (HIPAA).**
   - **PCI-DSS:** no card or payment data is described.
   - **HIPAA:** no health data or covered-entity relationship is described.
   - **Caveat:** both would change if the product handles payments, or if it serves health customers and the data becomes protected health information in their hands.

8. **No flags on the artifact as described: accessibility (ADA/WCAG/EAA).** The description covers no UI, so there is nothing to assess. If the tagline or consent flows ship on a web page or app, accessibility of those surfaces is a separate check.

## Missing facts

These decide which of the above apply.
- **Where users are:** EU/UK, California and other US states, Canada, elsewhere. This is the biggest gating fact.
- **How IP-based location is derived and stored:** whether the raw IP is retained, and at what granularity (city, region, or coarser).
- **Vendor role:** whether the email vendor is a processor/service provider or acts for its own purposes, and what the contract says. Where the vendor is located and where it processes data.
- **Purpose and consent:** why each field is collected, what users are told, and how consent or opt-out is captured.
- **Message type:** whether the emails are marketing, transactional, or both.
- **Retention:** how long the analytics DB keeps the data.
- **Security posture:** current controls, attestations, and any incident history, since these bear on the tagline's substantiation.
- **User ages:** whether minors can register.
- **Channels:** where the tagline will appear, such as ads, site, or sales collateral.

## Confirm with counsel

1. **The tagline, before it ships.** Whether the absolute and exclusive claims can be substantiated at all, and whether it is consistent with the data-sharing disclosures.
2. **The vendor arrangement.** Its legal characterization (processor/service provider vs. third party, and whether it is a "sale" or "share"), and whether the contract has the terms each applicable regime expects.
3. **Applicable jurisdictions.** Which privacy and email regimes actually apply once user locations are known, and the lawful-basis or notice requirements that follow.
4. **International transfers,** if the vendor or its sub-processors are outside the user's home jurisdiction.
5. **Retention and purpose limits** for the analytics store.
6. **Security representations.** What the company can accurately say about its security, given the vendor in the flow.

## Disclaimer

This is a risk flag list to prompt review by qualified counsel, not legal advice, and it makes no determination of compliance or non-compliance.