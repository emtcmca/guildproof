I don't have an artifact to verify yet. To run an independent verification, I need:

1. **The artifact itself** â€” the code, spec, prompt, API design, document, or deliverable you want verified
2. **The contract it claims to satisfy** â€” what it says it does, or what seams/decisions it must honor
3. **Any producer claims** â€” what the builder says about it (to be attacked as unverified)

**For example:**
- "Verify this Next.js API route against the spec in `docs/api-spec.md` and this PR description"
- "Check this system prompt against the requirements in the agent contract I'm pasting"
- "Review this auth middleware for correctness and abuse potential"

Paste or point me to what needs to be verified, and the contract it's supposed to satisfy. I'll read both cold and report:
- **Verdict** (VERIFIED / VERIFIED WITH GAPS / NOT VERIFIED, with BLOCKING yes/no)
- **Independence** (was it built in this conversation or did it arrive finished?)
- **Observable defects** â€” what I can demonstrate breaks the contract
- **Gaps I couldn't check** â€” axes that need confirmation
- **Claimed vs. actual** â€” where the artifact diverges from its claims

What should I verify?
