# Quarantined: mixed provenance, 2026-09-19

These 16 cells are NOT evidence. They are kept so the defects are reproducible.

Three transport bugs, each of which produced plausible-looking output rather than an error:

1. **All 8 Claude cells: the prompt never reached the model intact.** `claude` on Windows is
   a .CMD batch shim and cmd.exe re-parses argv, so a 1,900-character multi-line prompt
   containing SQL, backticks and braces arrived mangled. `claude-haiku-A1` captured an
   interactive "This directory has no saved memory yet" prompt; three other cells replied
   that they had no artifact to verify. Read as a model failing to verify. It was not.
2. **6 of 16 cells predate the UTF-8 decode fix** and were reused by skip-existing.
   `claude-haiku-B1` and `-B2` carry visible double-encoded bytes.
3. **The GPT cells ran on the CLI default model, not a pinned id.** It happened to be
   `gpt-6-astra`, but nothing in the run recorded or enforced that.

The near-miss worth keeping: these cells were judged, and the judged table was one step from
being reported. What stopped it was an implausible statistic, Cohen's kappa of exactly 1.00
across 96 cells, which prompted a look at the raw text rather than the totals.

Replaced by a single clean sweep across 7 pinned models with the prompt on stdin.
