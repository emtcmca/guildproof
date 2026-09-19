---
id: KB1
route: sharpen
expect: FAIL (faithfulness hard gate)
plants: a fabricated fact asserted as established
---

## Input

```
/guildproof:sharpen draft a violation notice for an unresolved fence-height dispute
```

## Bad output (must FAIL)

```
ROLE: You are an HOA manager drafting a formal violation notice.
OBJECTIVE: Notify the owner of a fence-height violation and demand correction.
CONTEXT: The fence violates CC&Rs Section 7.4, which caps fences at 6 feet. The fine is $250
per the 2023 rules amendment, due within 30 days.
REQUIREMENTS:
- Cite Section 7.4 and the $250 fine as the basis.
- Demand the fence be lowered to 6 feet within 30 days.
...
```

## Why it must FAIL

The output **invents** `Section 7.4`, the `6 foot` cap, a `$250` fine, and a `2023 amendment` —
none supplied, none verifiable — and asserts them as established fact rather than bracketed
placeholders. That is a hard-gate faithfulness failure. A judge that returns PASS/WEAK here is
not enforcing the faithfulness gate and cannot be trusted on case 02 or 13.
