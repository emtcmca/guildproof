I need the artifact and its contract to verify. Neither is present.

**Provide:**

1. **The artifact** â€” paste the code, spec, prompt, design doc, or other material you want verified
2. **Its contract** â€” what it claims to do, what boundaries it must honor, what acceptance criteria define "correct." If unstated, I'll derive it from the artifact, but say so.
3. **Context** â€” why this verification matters (security-critical? before merge? design gate?)

**Once you give me those three things, I will:**
- Attack it systematically across correctness, security, authorization, data integrity, and seam-enforcement axes
- Distinguish what I can demonstrate (observable evidence) from what I'm assessing (judgment)
- Return a blocking verdict: **VERIFIED** (survives every axis I could check), **VERIFIED WITH GAPS** (no defect found, but some axis couldn't be confirmed), or **NOT VERIFIED** (real defect breaks the contract)

Paste the artifact now, name the contract, and I'll begin.
