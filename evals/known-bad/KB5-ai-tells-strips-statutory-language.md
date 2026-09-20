---
id: KB5
route: lens
expect: FAIL (statutory terms of art stripped as "AI vocabulary")
plants: an ai-tells --fix output that rewrote governing-document language it should have left verbatim
---

## Input

```
/guildproof:lens --lens ai-tells --fix
```

Artifact under review (a violation notice quoting the recorded declaration):

```
Dear Owner,

A violation of the Declaration has been observed at the above address.

Article VII, Section 3 of the Declaration provides: "It shall be the obligation of each Owner to
maintain the exterior of the Unit in good repair. Timely compliance is vital to the preservation
of Association property values, and the Board shall have the right to foster compliance through
the remedies set forth herein."

Please correct the condition within thirty (30) days. As Ohio Revised Code 5312.11 requires, you
may request a hearing before the Board prior to imposition of any enforcement assessment.
```

## Bad output (must FAIL)

```
## ai-tells
- ❌ Tier 1 vocabulary: "vital", "foster", "preservation" — replace with plain words.
- ❌ Tier 1 vocabulary: "obligation" reads formal/inflated.

### Corrected version

Dear Owner,

We noticed a problem at your address.

Article VII, Section 3 of the Declaration says each Owner has to keep the outside of the Unit in
good shape. Keeping up with this really matters for property values, and the Board can encourage
compliance using the remedies listed.

Please fix it within 30 days. Under Ohio law you can ask for a hearing before any fine.
```

## Why it must FAIL

The lens rewrote **quoted, attributed, legally operative text**. Three separate carve-outs were
violated at once:

1. **Quoted material.** The declaration excerpt sits inside quotation marks and is attributed to
   Article VII, Section 3. Rewriting it makes the notice misquote a recorded instrument — the
   letter now claims the declaration says something it does not say.
2. **Statutory / contractual terms of art.** `obligation`, `shall`, and `vital` carry settled
   meaning in a governing document. "has to", "can encourage", and "really matters" are not
   synonyms; they change what the instrument does and weaken enforceability.
3. **Specific legal citation destroyed.** "As Ohio Revised Code 5312.11 requires" became "Under
   Ohio law", deleting the citation an owner needs to verify the claimed right.

This is the over-stripping failure mode of the `ai-tells` lens. Correct behavior: flag nothing
inside the quotation, leave the statutory language verbatim, **say why it was skipped** ("left
`vital` — statutory term inside a quoted provision"), and confine any suggestion to the
surrounding unquoted prose.

A judge that returns PASS here proves the lens's carve-outs are unenforced and that guildproof
will damage exactly the high-liability documents where accuracy matters most.
