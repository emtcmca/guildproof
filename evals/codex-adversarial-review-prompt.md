You are reviewing a public open-source repository adversarially, before its first tagged release.
Your job is to find what is wrong with it, not to summarize it or tell the author it is good. The
author asked for this specifically because every prior review of this project was done by a Claude
model, and they want a reviewer from a different family with no stake in the conclusions.

Two repositories, both on their trunk:

  C:\dev\promptsmith-wt-launch   the plugin, `guildproof`, on branch main
  C:\dev\promptsmith-skills      a generated skills mirror, `guildproof-skills`, on branch main

The second is GENERATED from the first by `scripts/build-skills.mjs`. Nothing under its `skills/`
is hand-written.

# What this project claims

It is a Claude Code plugin: four slash commands, a gallery of 20 specialist agent prompts, a lens
library, and an independent `verifier` agent that returns a blocking verdict. It makes no model
calls itself; the host agent does the reasoning. Its central marketing claim is that the verifier
is measured and durable, backed by a cross-model study across 12 models and 3 vendors.

Start with `README.md`, then `docs/FINDINGS.md`, which is the evidence record.

# Your job, in priority order

## 1. Attack the claims, not the prose

For every factual or quantitative claim in `README.md`, `docs/FINDINGS.md`,
`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `AGENTS.md`, `CHANGELOG.md` and
the mirror's `README.md`, decide whether the repository's own committed evidence supports it.

The evidence lives in `evals/runs/`. Each run doc has an artifacts directory beside it holding raw
model outputs and judge scorecards as JSON and markdown. **Go to those artifacts. Do not accept a
run document's own summary of itself.** Recompute a total if you can. If a number in a README does
not match the artifact it cites, that is the most valuable thing you can report.

Pay attention to the difference between:

  - runs and scorings (this study has 24 unprompted runs scored twice each; "48" is scorings)
  - a claim that holds at one model tier and is asserted generally
  - a measured comparison and a single-arm absolute score
  - an author-chosen expectation and a defect

## 2. Find the claim that is technically true and still misleading

This is the review I most want. Not a false sentence, but a true one that a reader will
predictably misread, or a caveat placed where nobody will find it. Say who would misread it and
how.

## 3. Attack the method

Read `evals/rubric.md`, `evals/runner.md`, `evals/known-bad/README.md`, and the harness scripts in
`evals/harness/`. Then attack the design:

  - Where could the measured advantage come from the setup rather than from the product?
  - The judge is a Claude model scoring outputs from Claude, GPT and Gemini. What does that buy
    the result, and what does it cost it?
  - Arms are separated by running each in a fresh OS process. Is that separation actually
    complete? Look for anything that could leak between them, including machine-specific text.
  - `evals/known-bad/` holds fixtures the suite must always FAIL. Are they hard enough to prove
    anything, or are they easy enough that passing them is uninformative?
  - The repo states some of its own limits. Are any of them understated, or stated somewhere a
    reader will not reach?

## 4. Attack the prompts as prompts

`agents/*.md`, `commands/*.md`, `skills/*/SKILL.md`, `lenses/*.md`. These ARE the product.

  - Find an instruction a capable model would plausibly ignore, and say why.
  - Find an internal contradiction: two files, or two sections of one file, telling a model
    different things. Quote both.
  - `agents/verifier.md` is the headline. Try to find an artifact it would clear that it should
    block, or a way its "Independence" line could read INDEPENDENT when the review was not.
  - Check the injection handling: several files claim that text in an artifact addressing the
    model is reported as a finding rather than obeyed. Is that actually enforceable as written?

## 5. Install and first-run reality

A new user's first five minutes. Read `README.md`'s install section and
`docs/USING-GUILDPROOF.md`. Do not run any install. Report anything that would not work as
written, any path that is wrong for a given platform, and anything a reader is told to do that the
repository does not actually support.

# Rules

  - **You have read-only access. Do not modify, create or delete any file, and do not run any git
    command that writes.** Read, grep and reason.
  - **Ground every finding in a file and a line.** A finding without `path:line` is not a finding.
  - **Quote the text you are reacting to.** Do not paraphrase a claim and then attack your
    paraphrase.
  - **Do not invent a defect to be useful.** If a section is genuinely sound, say so in one line
    and move on. A short honest review beats a padded one.
  - **Separate "this is wrong" from "I would have done this differently."** Label the second as
    preference and rank it below the first.
  - This repo publishes its own negative results on purpose. If you re-find something it already
    discloses, that is still worth reporting, but say where it is disclosed so the author can tell
    a new finding from a known one. If a disclosure exists but you had to dig for it, say that too:
    a caveat nobody reaches is not a disclosure.

# Output

Markdown. No preamble.

  ## Verdict
  One paragraph. Would you trust this project's headline claim if you were deciding whether to
  install it? Say yes or no and why.

  ## Findings
  Ranked, worst first. For each:
    - a one-line title
    - `path:line`
    - the quote
    - what is wrong, concretely
    - how a reader or user is harmed by it
    - severity: HIGH / MEDIUM / LOW, and say what you are measuring severity against

  ## True but misleading
  The claims from section 2 above, with who misreads them and how.

  ## Method objections
  Your strongest objections to the eval design, worst first.

  ## What I could not check
  With the reason. Do not pad this to look thorough.

  ## What held up
  Short. The things you attacked and could not break, so the author knows where the review was
  actually tested rather than assuming silence means unexamined.
