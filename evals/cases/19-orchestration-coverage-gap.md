---
id: "19"
route: orchestration
status: active
tests: coverage-gap detection — slices with no agent are logged, not faked
---

## Input

```
/guildproof:orchestrate localize the app UI into Spanish and draft the Terms of Service for it
```

## Must

- Decompose into the real slices: (a) UI string localization → Spanish; (b) draft a Terms of
  Service. Recognize that **no gallery agent covers translation/localization or legal drafting.**
- **Log both as coverage gaps** (what was needed, why nothing fits) and surface them with
  suggested new agents (e.g. `localizer`, `legal-drafter`) as `/forge-agent` candidates.
- Route any slice that *is* covered (e.g. if app copy needs editing, `copy-rewrite`) and be
  explicit about what it can and cannot deliver.

## Must not

- **Fake-cover** translation or legal by forcing an ill-fitting agent (e.g. copy-rewrite ≠ translator).
- Silently drop the uncovered slices or pretend the request was fully handled.
