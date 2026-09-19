---
id: "06"
route: lens
command: /guildproof:lens
expected-lenses: [skeptic, editorial]
tests: dogfood — lens-review a weak prompt; findings map to prompt-quality issues
---

## Input

```
/guildproof:lens --lens skeptic,editorial
```

Artifact under review (a system prompt, pasted with the command):

```
You are a helpful assistant. Be concise and professional. Help the user with whatever they
need. Always be accurate and don't make mistakes. Use good judgment.
```

## Must

- Flag the prompt's real weaknesses: no concrete role/domain; "concise", "professional",
  "good judgment" are unmeasurable; "don't make mistakes" is unactionable; no output contract;
  no guardrails; no self-check.
- Findings ✅/⚠️/❌, worst-first, each pointing at the specific phrase.
- Top-3 fixes by impact + the offer to run `/guildproof:sharpen` (or note `prompt-engineer`).

## Must not

- Rewrite the prompt (findings only).
- Accept the vague instructions as adequate.
