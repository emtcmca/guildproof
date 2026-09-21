<!--
Delete whatever does not apply. A one-line PR with a one-line description is fine;
this template is a reminder of what a reviewer will ask, not a form to fill out.
-->

## What this changes, and why

<!-- One or two sentences. What was wrong or missing before this PR? -->

## Kind of change

- [ ] New or edited **lens** (`lenses/`)
- [ ] New or edited **agent** (`agents/`)
- [ ] **Command** or engine change (`commands/`, `skills/`)
- [ ] **Evals or harness** (`evals/`)
- [ ] **Docs** only
- [ ] Something else:

## If you changed a prompt

**Say what you ran it against and what changed in the output. "Should be better" is not
reviewable** — it is the one thing a reviewer cannot check, and this repo has published a retired
claim for exactly that reason.

- Ran it against:
- Before / after, or the specific behavior that changed:
- Model and tier you tried it on:

<!--
If you are making a quality CLAIM rather than a change, the bar is higher and it is worth
knowing up front: this repo requires a REDUCED ARM before it publishes a claim that a prompt
causes an effect. A third arm carrying only one section of `verifier.md` reproduced that
prompt's entire measured advantage, which is why. See docs/FINDINGS.md, "Construct validity".
You do not need to run a benchmark to contribute a prompt. You need one to claim it works.
-->

## Checks

<!-- Both spend nothing: no model calls, no keys, no network. -->

- [ ] `node scripts/validate.mjs` exits 0
- [ ] `node scripts/validate.mjs --selftest` still catches its own fixtures
- [ ] `python evals/harness/selftest-crossmodel.py` exits 0 *(only if you touched `evals/harness/`)*
- [ ] Counts I stated in docs were taken **on a ref** (`git ls-tree`), not from a working directory

## Constraints this repo does not bend

- [ ] **No dependencies, no API keys, no model calls inside the plugin.** Zero-dependency is
      architectural here: the plugin is method and structure, and the host agent does the reasoning.
- [ ] Nothing I added claims a measurement that is not in `evals/runs/`
- [ ] I read the whole diff

<!--
Security issues do not go in a PR. See SECURITY.md — use private vulnerability reporting.
-->
