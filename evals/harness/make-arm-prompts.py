"""Generate the reduced arms of a specialist-prompt study, by extraction rather than by hand.

WHY THIS IS A SCRIPT AND NOT A FILE SOMEONE WROTE
-------------------------------------------------
The verifier study measures a full specialist prompt (arm B) against a bare model (arm A). The
obvious objection to the result is that most of the gap could be bought by simply *naming the
sections the output must contain* — no method, no adversarial stance, no guardrails. If that were
true, the honest claim would shrink from "this prompt changes how a model reviews work" to "telling
a model which headings to emit makes it emit those headings."

Arm C tests that. It has to be a real subset of the shipped prompt, not a paraphrase written by
the same person who wants arm B to win, so it is **extracted mechanically from the shipping file**
and regenerated on demand. If `agents/verifier.md` is reworded, this is re-run and the arm follows;
if a heading is renamed, this exits non-zero instead of silently emitting a truncated arm.

WHAT ARM C DELIBERATELY DOES AND DOES NOT CONTAIN
-------------------------------------------------
It contains the frontmatter-free body of exactly one section: `## Output contract`. It does not
contain Objective, Operating principles, Inputs, Method, Constraints / guardrails, or When unsure.

Note what that means for the scored checklist, because it is the whole point and it is recorded
here **before the arm was ever run**: five of the six scored behaviors are named in the output
contract (tri-state verdict, BLOCKING line, Independence line, severity-ranked defects, a receipt
per clean axis). The sixth — *does not rewrite the code* — lives in `## Constraints / guardrails`,
which arm C does not receive. So the pre-registered prediction is:

    Arm C scores high on items 1, 2, 3, 4 and 6, and NOT on item 5.

That prediction is falsifiable in both directions and it is the reason the arm is worth running.
If it holds, the measured gap is mostly a formatting effect and the README must say so. If arm C
also refrains from rewriting, the contract is doing more than naming headings. If arm C scores
*low* on items it was explicitly handed, then naming a section is not sufficient even for
compliance, which is a finding about instruction-following rather than about this prompt.

    python make-arm-prompts.py            write the arms, report what changed
    python make-arm-prompts.py --check    verify the arms on disk match the source, exit 1 if not
"""

import argparse
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = pathlib.Path(__file__).parent
REPO = HERE.parent.parent
OUT_DIR = REPO / "evals" / "benchmarks" / "arms"

# Each reduced arm: which source file, which sections to keep, and the one-line reason it exists.
ARMS = [
    {
        "out": "verifier-output-contract-only.md",
        "source": "agents/verifier.md",
        "keep": ["Output contract"],
        "why": ("Output contract only: the required sections, with no method, no adversarial "
                "stance and no guardrails. Isolates how much of arm B's advantage is bought by "
                "naming the headings the output must carry."),
    },
]

HEADING = re.compile(r"^## +(.+?)\s*$")


def split_sections(text):
    """Return (preamble, [(heading, body)]) for a `## `-sectioned markdown file."""
    lines = text.splitlines()
    # Drop YAML frontmatter: it is host metadata, not instruction, and a reduced arm must not
    # inherit a `role:` or `voice:` line that the section it keeps does not contain.
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:
            raise ValueError("frontmatter opened but never closed")
        lines = lines[end + 1:]
    preamble, sections, current = [], [], None
    for line in lines:
        m = HEADING.match(line)
        if m:
            current = (m.group(1), [])
            sections.append(current)
        elif current is None:
            preamble.append(line)
        else:
            current[1].append(line)
    return "\n".join(preamble).strip(), [(h, "\n".join(b).strip()) for h, b in sections]


def build(arm):
    src_path = REPO / arm["source"]
    if not src_path.exists():
        raise SystemExit(f"ERROR: source not found: {src_path}")
    _, sections = split_sections(src_path.read_text(encoding="utf-8"))
    have = [h for h, _ in sections]
    missing = [k for k in arm["keep"] if k not in have]
    if missing:
        # Loud, not silent. A renamed heading would otherwise produce an arm that quietly lacks
        # the thing it exists to test, and the run would read as a null finding about the
        # contract instead of a bug in this script.
        raise SystemExit(
            f"ERROR: {arm['source']} has no section(s) {missing}.\n"
            f"  Sections present: {have}\n"
            f"  A heading was renamed. Fix ARMS in this file rather than letting the arm ship "
            f"without the section it is meant to isolate.")
    body = "\n\n".join(b for h, b in sections if h in arm["keep"])
    dropped = [h for h in have if h not in arm["keep"]]
    # A bare list of required sections is not a usable system prompt on its own, so it gets the
    # minimum framing that makes it one. This sentence is the ONLY authored text in the arm, it
    # is deliberately free of method, stance and severity language, and it is identical for
    # every reduced arm so it cannot advantage one.
    framing = ("Review the artifact the user provides. Your response must follow this output "
               "contract:\n\n")
    prompt = framing + body + "\n"
    # PROVENANCE GOES BESIDE THE FILE, NEVER INSIDE IT. The first version of this script wrote a
    # `<!-- GENERATED ... Why: isolates how much of arm B's advantage ... -->` header into the
    # prompt, which the runner then sends verbatim as the system prompt. The model would have
    # been told it was a reduced arm in an experiment about its own prompt — contaminating the
    # exact comparison the arm exists to make, in the direction of making the arm look better.
    # Caught before any cell was generated. An arm prompt contains only what the arm is.
    provenance = {
        "generated_by": "evals/harness/make-arm-prompts.py",
        "source": arm["source"],
        "kept_sections": arm["keep"],
        "dropped_sections": dropped,
        "framing_sentence": framing.strip(),
        "why": arm["why"],
        "note": ("Do not paste any of this into the prompt file. It names the experiment, and a "
                 "model that reads it knows it is in one."),
    }
    return prompt, provenance


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify what is on disk matches the source; write nothing")
    a = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stale = []
    for arm in ARMS:
        want, provenance = build(arm)
        dest = OUT_DIR / arm["out"]
        prov_dest = dest.with_suffix(".provenance.json")
        current = dest.read_text(encoding="utf-8") if dest.exists() else None
        rel = dest.relative_to(REPO).as_posix()

        # The prompt must contain no experiment metadata at all. Checked here rather than trusted,
        # because this is the one contamination that would flatter the result.
        leaks = [w for w in ("GENERATED", "arm B", "arm C", "isolate", "Isolates", "benchmark",
                             "experiment", "make-arm-prompts") if w in want]
        if leaks:
            raise SystemExit(f"ERROR: {rel} would carry experiment metadata {leaks}. An arm "
                             f"prompt contains only what the arm is.")

        if current == want:
            print(f"  ok      {rel}  ({len(want)} chars, matches {arm['source']})")
        elif a.check:
            reason = "absent" if current is None else "differs from its source"
            print(f"  STALE   {rel}  ({reason})")
            stale.append(rel)
            continue
        else:
            dest.write_text(want, encoding="utf-8")
            print(f"  written {rel}  ({len(want)} chars, from {arm['source']}; "
                  f"kept {arm['keep']}, dropped {len(provenance['dropped_sections'])} sections)")
        if not a.check:
            prov_dest.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    if stale:
        print(f"\n{len(stale)} arm prompt(s) are stale. Run without --check to regenerate.")
        print("A reduced arm that no longer matches the prompt it was cut from measures history.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
