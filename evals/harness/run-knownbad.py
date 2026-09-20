#!/usr/bin/env python3
"""B4, known-bad half: prove the judge can still say no, at the commit being tagged.

The six fixtures in `evals/known-bad/` each pair a case input with a DELIBERATELY WRONG
output. Every one must be graded FAIL. If any scores PASS or WEAK, the judge is
rubber-stamping and no green run in this repo means anything.

Two design points carry the whole result:

1. **The fixture file states the answer, so the judge must never see the file.** Each
   fixture carries `expect: FAIL`, a `plants:` line naming the planted defect, a heading
   that reads "Bad output (must FAIL)", and a closing "Why it must FAIL" section that
   explains the defect in detail. Handing any of that to a judge measures nothing but
   reading comprehension. `neutralize()` strips all four and renames the heading. Run
   `--show KB4` to read the exact bytes a judge receives and audit that for yourself.

2. **Blinding is structural, not promised.** Each judge is a fresh OS process with no
   channel to the authoring conversation. An earlier version of this repo's eval work ran
   arms as in-harness subagents, and the harness relayed the parent conversation's latest
   user message into every one of them; two cells answered that message instead of doing
   the task. A promise not to look is not blinding.

Usage:
    python evals/harness/run-knownbad.py --check          # what this machine can run, spends nothing
    python evals/harness/run-knownbad.py --show KB4        # the exact judge prompt, spends nothing
    python evals/harness/run-knownbad.py                   # run all 6 fixtures, k=2
    python evals/harness/run-knownbad.py --only KB4 --k 1  # one fixture, one judge
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
REPO = HERE.parent.parent                      # evals/harness -> evals -> repo root
KB_DIR = REPO / "evals" / "known-bad"
RUBRIC = REPO / "evals" / "rubric.md"

# Pinned, never an alias. An alias resolves to whatever the vendor currently points at,
# which silently changes what a published number was measured on.
#
# Sonnet judges and Haiku never: measured against a two-Opus consensus over 69 cells,
# Sonnet scored Cohen's kappa 0.68 while Haiku scored 0.51 with a bias that flipped
# direction depending on the specialist. Haiku stays usable as a subject, not a judge.
JUDGE_MODEL = "claude-sonnet-5"

# --- the positive control, and why it is not optional -------------------------------------
# Six known-bad fixtures all scoring FAIL is also exactly what a judge with a FAIL bias
# produces. The set proves the judge CAN say no; on its own it says nothing about whether it
# can still say yes, and a judge that only says no is as useless as one that only says yes.
#
# So `--positive` runs one known-GOOD output through the identical path: same rubric, same
# prompt scaffold, same model, same blinding. The output is a real verifier run from the
# 2026-09-20 cross-model study's guildproof arm, on the same route as KB4, scored 6 of 6 by
# two blinded judges there. It must NOT come back FAIL.
POSITIVE_CONTROL = {
    "output": REPO / "evals" / "runs" / "2026-09-20-crossmodel-v2-artifacts" / "claude-opus-B1.md",
    "input": REPO / "evals" / "benchmarks" / "fixtures" / "v2-invoice-subtle.md",
    "meta": {"route": "gallery-agent", "agent": "verifier"},
}

# `claude -p` executes this machine's SessionStart hooks, which prepend machine-specific
# text (a vault read-back, a commitments line) to the model's own output. It is identical
# across cells and carries no signal, but it must not reach the verdict parser.
HOOK_NOISE = re.compile(
    r"(?is)^.*?(?:=== VAULT RECALL.*?===.*?|Q lane:.*?$)\s*", re.MULTILINE
)


def exe(name):
    """Resolve a CLI to a real executable path, or None if it is not installed.

    On Windows npm installs both a POSIX shell script (`claude`) and a `.CMD` shim, and
    CreateProcess can only launch the latter. shutil.which honours PATHEXT and returns the
    .CMD, so this avoids a WinError 2 that otherwise reads as "not installed".
    """
    return shutil.which(name)


def neutralize(text):
    """Turn a known-bad fixture into a blind grading task.

    Removes every part of the file that states or hints at the expected verdict:
      * the `expect:` and `plants:` frontmatter lines (route/agent are kept - they select
        the rubric section and are legitimate context, not the answer),
      * the "## Why it must FAIL" section and everything after it,
      * the "(must FAIL)" parenthetical in the output heading.

    Returns (input_text, output_text, meta) or raises on a fixture whose shape changed.
    A silent partial strip is the dangerous failure here, so every step is asserted.
    """
    # --- frontmatter: keep route/agent, drop expect/plants -------------------------
    m = re.match(r"(?s)^---\n(.*?)\n---\n(.*)$", text)
    if not m:
        raise ValueError("fixture has no frontmatter block")
    fm_raw, body = m.group(1), m.group(2)
    meta = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for leaky in ("expect", "plants"):
        meta.pop(leaky, None)

    # --- split the body on its three headings --------------------------------------
    # KB2 and KB5 carry a nested "## <lens-name>" heading INSIDE the output section, so
    # the output runs to the "Why it must FAIL" heading, not to the next "##".
    im = re.search(r"(?m)^## Input\s*$", body)
    om = re.search(r"(?m)^## Bad output[^\n]*$", body)
    wm = re.search(r"(?m)^## Why it must FAIL\s*$", body)
    if not (im and om and wm):
        raise ValueError("fixture is missing one of: '## Input', '## Bad output', '## Why it must FAIL'")

    input_text = body[im.end():om.start()].strip()
    output_text = body[om.end():wm.start()].strip()

    # The answer must not survive anywhere in what we send.
    for banned in ("must FAIL", "Why it must FAIL", "expect:", "plants:"):
        for blob in (input_text, output_text):
            if banned in blob:
                raise ValueError(f"leak: {banned!r} survived the strip")

    # A four-string blocklist was not enough, and this is how it failed.
    #
    # KB3's bad-output block carried `// string-interpolated -> SQL injection` and
    # `// returns the full internal entity` INSIDE the code. Neither matched any banned string, so
    # the judge was handed the name of the planted defect. Its transcript then said: "The overall
    # pattern also matches the `evals/known-bad/` fixtures. The rubric requires the harness to FAIL
    # those, so the failure here is expected." A judge that knows it is looking at a fixture is not
    # a blinded judge, and the 6-of-6 result did not mean what it claimed for that cell.
    #
    # An author annotating a planted bug is the natural way to write one of these files and the
    # exact thing that must not ship in the artifact. So this checks for the SHAPE: a source
    # comment whose text names a defect or flags itself as deliberate. It is not a general
    # leak detector, which is why the shipped fixtures are also read by a human before trusting a
    # gate result. Caught by an adversarial review from a different model family, after several
    # same-family passes missed it.
    TELLS = (r"injection|vulnerab|insecure|unsafe|exploit|leak|defect|deliberate|on purpose"
             r"|intentional|wrong|missing|should (?:be|not)|TODO|FIXME|XXX|HACK|BUG")
    for m in re.finditer(rf"(?im)(?://|--|#)[^\n]*(?:{TELLS})[^\n]*$", output_text):
        raise ValueError(
            f"leak: the bad-output block carries a comment naming its own defect, which tells the "
            f"judge the answer:\n    {m.group(0).strip()}\n"
            f"Remove the annotation. A real bad output does not label its own bugs.")
    return input_text, output_text, meta


def build_prompt(input_text, output_text, meta, rubric):
    """Assemble the judge prompt. The judge is told the route so it grades against the
    right rubric section, and is told nothing about where the output came from."""
    route = meta.get("route", "unknown")
    agent = meta.get("agent", "")
    which = f"route `{route}`" + (f", agent `{agent}`" if agent else "")
    return f"""You are an independent judge grading ONE output produced by a prompt-engineering
toolkit. You did not produce this output and you know nothing about it beyond what follows.

Grade it against the rubric below. The relevant rubric section is the one for {which}.

Follow the rubric's stance exactly: it is adversarial. Your job is to break the output, not
to bless it. Default to weak or fail when uncertain. Quote the part of the output you are
reacting to for every mark you give.

===== RUBRIC =====
{rubric}
===== END RUBRIC =====

===== THE CASE INPUT THE TOOLKIT WAS GIVEN =====
{input_text}
===== END CASE INPUT =====

===== THE OUTPUT TO GRADE =====
{output_text}
===== END OUTPUT =====

Score every applicable structural invariant and every applicable quality dimension for
this route. One mark each, with a one-line reason and a quote.

Then apply the rubric's verdict rule literally: PASS if no fail marks, WEAK if there are
weak marks but no fail marks, FAIL if there is any fail mark.

End your reply with exactly one final line, and nothing after it:
VERDICT: PASS
or
VERDICT: WEAK
or
VERDICT: FAIL
"""


def run_judge(prompt, model):
    """One judge, one fresh process.

    The prompt goes on STDIN and must never go on argv. On Windows `claude` resolves to a
    .CMD batch shim and cmd.exe re-parses its arguments, which silently mangled prompts
    containing SQL and backticks in an earlier run - and every one of these fixtures
    contains SQL or backticks. The command line also caps at 8191 characters, and this
    prompt is well past that.
    """
    claude = exe("claude")
    if not claude:
        raise SystemExit("claude CLI not on PATH (npm i -g @anthropic-ai/claude-code)")
    cmd = [claude, "-p", "--model", model, "--no-session-persistence"]

    # ANTHROPIC_API_KEY shadows the subscription login even when it has no credits, and
    # the resulting error reads like an account problem rather than an env problem.
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)

    # encoding/errors are explicit: text=True alone decodes with the Windows ANSI
    # codepage, and a single em-dash in model output crashed the reader thread and left
    # stdout as None, surfacing as an AttributeError forty lines from the cause.
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, env=env)
    out = (r.stdout or "").strip()
    if not out:
        raise RuntimeError(f"empty judge output (exit {r.returncode}): {(r.stderr or '')[:400]}")
    return out


def parse_verdict(raw):
    """Read the verdict off the judge's last VERDICT line.

    Returns (verdict, cleaned_text). An unparseable reply returns None rather than a
    guess: an unscored cell is unmeasured, not passing.
    """
    cleaned = HOOK_NOISE.sub("", raw).strip()
    hits = re.findall(r"(?mi)^\s*\**VERDICT:\**\s*\**(PASS|WEAK|FAIL)\**", cleaned)
    return (hits[-1].upper() if hits else None), cleaned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report what this machine can run; spends nothing")
    ap.add_argument("--show", metavar="KBn", help="print the exact judge prompt for one fixture; spends nothing")
    ap.add_argument("--only", metavar="KBn", help="run one fixture")
    ap.add_argument("--positive", action="store_true",
                    help="grade a known-GOOD output through the identical path; it must NOT fail")
    ap.add_argument("--k", type=int, default=2, help="judges per fixture (default 2)")
    ap.add_argument("--out", default=None, help="artifacts directory")
    args = ap.parse_args()

    # The rubric and the fixtures contain checkmark and cross glyphs, and a Windows console
    # defaults to the cp1252 codepage, which cannot encode them. Without this, --show dies
    # on a UnicodeEncodeError that looks like a bug in the fixture rather than in printing.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    fixtures = sorted(p for p in KB_DIR.glob("KB*.md"))
    if not fixtures:
        raise SystemExit(f"no KB fixtures found under {KB_DIR}")
    if not RUBRIC.exists():
        raise SystemExit(f"rubric not found at {RUBRIC}")
    rubric = RUBRIC.read_text(encoding="utf-8")

    if args.check:
        claude = exe("claude")
        print(f"fixtures found : {len(fixtures)} ({', '.join(p.name.split('-')[0] for p in fixtures)})")
        print(f"rubric         : {RUBRIC} ({len(rubric.splitlines())} lines)")
        print(f"judge model    : {JUDGE_MODEL} (pinned)")
        print(f"claude CLI     : {claude or 'NOT ON PATH - npm i -g @anthropic-ai/claude-code'}")
        if os.environ.get("ANTHROPIC_API_KEY"):
            print("note           : ANTHROPIC_API_KEY is set; it is stripped per call so the "
                  "subscription login is used")
        ok = True
        for p in fixtures:
            try:
                neutralize(p.read_text(encoding="utf-8"))
                print(f"  {p.name}: strips cleanly")
            except Exception as e:
                ok = False
                print(f"  {p.name}: SHAPE CHANGED - {e}")
        raise SystemExit(0 if ok and claude else 1)

    if args.show:
        p = next((f for f in fixtures if f.name.startswith(args.show)), None)
        if not p:
            raise SystemExit(f"no fixture matching {args.show}")
        i, o, meta = neutralize(p.read_text(encoding="utf-8"))
        print(build_prompt(i, o, meta, rubric))
        raise SystemExit(0)

    if args.only:
        fixtures = [f for f in fixtures if f.name.startswith(args.only)]
        if not fixtures:
            raise SystemExit(f"no fixture matching {args.only}")

    out_dir = pathlib.Path(args.out) if args.out else (
        REPO / "evals" / "runs" / "2026-09-20-b4-knownbad-artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.positive:
        pc = POSITIVE_CONTROL
        for p in (pc["output"], pc["input"]):
            if not p.exists():
                raise SystemExit(f"positive control file missing: {p}")
        prompt = build_prompt(pc["input"].read_text(encoding="utf-8").strip(),
                              pc["output"].read_text(encoding="utf-8").strip(),
                              pc["meta"], rubric)
        verdicts = []
        for k in range(1, args.k + 1):
            cell = out_dir / f"POSITIVE-judge{k}.md"
            if cell.exists():
                v, _ = parse_verdict(cell.read_text(encoding="utf-8"))
            else:
                print(f"positive control judge{k}: running...", flush=True)
                v, cleaned = parse_verdict(run_judge(prompt, JUDGE_MODEL))
                cell.write_text(cleaned, encoding="utf-8")
            print(f"positive control judge{k}: {v}")
            verdicts.append(v)
        ok = bool(verdicts) and all(v in ("PASS", "WEAK") for v in verdicts)
        print(f"\nPOSITIVE CONTROL: {' / '.join(str(v) for v in verdicts)}")
        print("  -> the judge can still say yes; the 6-of-6 FAIL result is not a FAIL bias" if ok
              else "  -> *** the judge failed a known-good output: it has a FAIL bias and B4 "
                   "proves nothing ***")
        sys.exit(0 if ok else 1)

    # The commit under test, recorded with the result. B4's whole claim is "at the exact
    # commit being tagged", which is meaningless without the ref.
    try:
        ref = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                             text=True, encoding="utf-8", errors="replace").stdout.strip()
    except Exception:
        ref = "unknown"

    results = []
    for p in fixtures:
        kb = p.name.split("-")[0]
        i, o, meta = neutralize(p.read_text(encoding="utf-8"))
        prompt = build_prompt(i, o, meta, rubric)
        for k in range(1, args.k + 1):
            cell = out_dir / f"{kb}-judge{k}.md"
            if cell.exists():                      # resume: never re-spend on a done cell
                verdict, _ = parse_verdict(cell.read_text(encoding="utf-8"))
                print(f"{kb} judge{k}: {verdict} (cached)")
                results.append({"fixture": kb, "judge": k, "verdict": verdict, "cached": True})
                continue
            print(f"{kb} judge{k}: running...", flush=True)
            try:
                raw = run_judge(prompt, JUDGE_MODEL)
            except Exception as e:
                print(f"{kb} judge{k}: ERROR {e}")
                results.append({"fixture": kb, "judge": k, "verdict": None, "error": str(e)})
                continue
            verdict, cleaned = parse_verdict(raw)
            cell.write_text(cleaned, encoding="utf-8")
            print(f"{kb} judge{k}: {verdict}")
            results.append({"fixture": kb, "judge": k, "verdict": verdict, "cached": False})

    # --- tabulate -------------------------------------------------------------------
    by_fixture = {}
    for r in results:
        by_fixture.setdefault(r["fixture"], []).append(r["verdict"])

    print("\n=== B4, known-bad half ===")
    print(f"commit under test : {ref}")
    print(f"judge             : {JUDGE_MODEL}, k={args.k}, blinded (fixture answer stripped)")
    print()
    correct = 0
    for kb in sorted(by_fixture):
        vs = by_fixture[kb]
        all_fail = bool(vs) and all(v == "FAIL" for v in vs)
        correct += 1 if all_fail else 0
        mark = "correctly FAILED" if all_fail else "*** DID NOT FAIL ***"
        print(f"  {kb}: {' / '.join(str(v) for v in vs)}  -> {mark}")
    total = len(by_fixture)
    print(f"\nKB fixtures correctly failed: {correct} of {total}")

    # The gate is only meaningful over the whole set. A filtered run reports its cells and
    # withholds the verdict rather than printing a FAIL that just means "you passed --only".
    if args.only:
        gate = correct == total
        print(f"GATE: not evaluated - filtered run ({args.only}). "
              f"Run without --only to score the gate.")
    else:
        gate = correct == total == len(list(KB_DIR.glob("KB*.md")))
        print("GATE: PASS - the judge can still say no" if gate
              else "GATE: FAIL - fix the rubric or the judge before trusting any green run")

    summary = {"benchmark": "B4-knownbad", "commit": ref, "judge_model": JUDGE_MODEL,
               "k": args.k, "correctly_failed": correct, "total": total,
               "gate": "PASS" if gate else "FAIL", "cells": results}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nartifacts: {out_dir}")
    sys.exit(0 if gate else 1)


if __name__ == "__main__":
    main()
