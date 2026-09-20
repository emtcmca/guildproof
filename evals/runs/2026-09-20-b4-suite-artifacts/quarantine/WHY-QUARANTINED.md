# Why these 12 cells are quarantined

**Cases 01 through 06, producer and judge cells, 2026-09-20.** Six command-route cases: two
`sharpen`, two `forge`, two `lens`.

These are kept rather than deleted so the defect stays reproducible. They are **not** valid
results and must not be counted, quoted, or averaged into any scorecard.

## The defect

The producer was graded against an output contract it was never given.

For a command route, the **command file carries the output contract**, not the engine.
`skills/prompt-engineering/SKILL.md:190` says so outright: *"LENS → findings list (no template;
see /lens command)"*. The per-lens block layout, the ✅/⚠️/❌ finding prefixes, the worst-first
ordering, the top-3-fixes list and the closing `/guildproof:sharpen` offer live in
`commands/lens.md:80-98` and nowhere else.

`run-suite.py` bundled the engine, the lens library and the output templates into the producer's
system prompt. It did not bundle the command file. So the producer saw the method and not the
contract, then a judge scored it against `evals/rubric.md`, which encodes that contract.

Cases 05 and 06 failed on exactly the four items that only the command file defines. Those are
harness failures wearing a product failure's clothes.

## What it would have looked like if it had shipped

A scorecard reading roughly "the `/lens` route does not follow its own output contract,"
published at a release tag. That is a false claim about the product, and the third one this
harness nearly produced.

## The pattern, which is the useful part

This was the **third** fidelity bug in this runner, and all three had one shape: **a real user
has a file that the transport was not handing over.**

1. The engine resolves its lens library and templates from `${CLAUDE_PLUGIN_ROOT}`, which does
   not exist under `claude -p`. The producer said it could not load any lens, and the judge
   correctly failed it. Cases 01-04 came back all FAIL.
2. `/forge-agent` is contracted to seed a new prompt from a close gallery match. `agents/` was
   not bundled, so the output said *"I could see only their one-line descriptions here, not their
   bodies, so I didn't adapt from them"* and failed the case's first must item. Case 03 went
   FAIL to WEAK once the gallery was supplied.
3. This one: the command file, and with it the output contract.

Each was caught by reading the judge's actual reasoning on a failure instead of accepting the
verdict. **Four straight FAILs on the most central routes is a harness smell, not a result** — the
same tell as a Cohen's κ of exactly 1.00 across 96 cells, which is what caught four transport bugs
in the cross-model study one step before its numbers were reported.

## What stands

Cases 07 through 10 are **not** affected and were not quarantined. Gallery agents are dispatched
with their own agent file, and `agents/<name>.md` is self-contained: there is no command file in
that path to withhold. Their bundle is the agent plus the lens library plus the templates, which
is what an install gives a dispatched agent.

## To reproduce, or to re-run properly

```bash
python evals/harness/run-suite.py --only 01,02,03,04,05,06
```

The fix is in `build_system_bundle()`; `ROUTE_COMMANDS` maps each route to its command file. To
see exactly what a producer now receives, without spending anything:

```bash
python evals/harness/run-suite.py --show 05
```
