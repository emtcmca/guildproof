"""Blind the cross-model cells, then score them with two Sonnet judges per target.

WHY SONNET, AND WHY NOT THE WORKFLOW HARNESS
--------------------------------------------
Judge choice is measured, not assumed. Against a two-Opus consensus on 69 cells of the
earlier small-tier run, Sonnet scored kappa 0.68 with a 3-point present-rate gap, while
Haiku scored kappa 0.51 with a bias that flipped direction by specialist (too generous on
debugger and api-reviewer, too harsh on security-review). A judge whose error direction
depends on the thing being judged would corrupt exactly the per-target comparison this
run reports. So: Sonnet.

Judges run through `claude -p` in a fresh process for the same reason the arms do. The
Claude Code workflow harness relays the parent conversation's latest user message to every
subagent, and having removed that channel from the arms it would be incoherent to leave it
in place for the scorers.

WHICH CELLS THIS SCORES
-----------------------
`--cells` defaults to the same directory `run-crossmodel.py --outdir` defaults to, so the
published sequence scores the cells it just generated. It did not used to: this file hard-coded
`runs/2026-09-20-crossmodel-v2-artifacts` while the runner wrote to `out-crossmodel`, so
anyone following our own reproduce instructions paid for fresh answers and then re-scored our
committed historical ones. See `crossmodel_cells.py` for the full account.

Re-scoring the committed run is still supported and now has to be named:

    python judge-crossmodel.py --blind --cells evals/runs/2026-09-20-crossmodel-v2-artifacts

Usage:
    python judge-crossmodel.py --blind            build the judge bundles and the label key
    python judge-crossmodel.py --judge            run 2 Sonnet judges per target
    python judge-crossmodel.py --tabulate         join scorecards to the key and report
"""

import argparse
import collections
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import crossmodel_cells as cc

HERE = pathlib.Path(__file__).parent

# Set by resolve_paths() from --cells before any command runs. Deliberately not given a
# working default at import time: a module-level guess is what made the old hard-coded path
# invisible, because every command silently had somewhere valid to go.
CELLS = BUNDLES = SCORES = KEY = None


def resolve_paths(cells_arg):
    """Point every derived path at the chosen cells directory, and say so out loud."""
    global CELLS, BUNDLES, SCORES, KEY
    CELLS = cc.resolve_cells_dir(HERE, cells_arg)
    BUNDLES = CELLS / "judge-bundles"
    SCORES = CELLS / "scorecards"
    KEY = CELLS / "label-key.csv"
    print(f"cells dir: {CELLS}")
    if not CELLS.exists():
        sys.exit(
            f"ERROR: no such cells directory.\n"
            f"  Generate cells first:  python run-crossmodel.py --input "
            f"evals/benchmarks/fixtures/v2-invoice-subtle.md\n"
            f"  Or score a committed run: --cells evals/runs/2026-09-20-crossmodel-v2-artifacts"
        )
    n_cells = len(list(CELLS.glob("*-[AB][12].md")))
    print(f"cell files present: {n_cells} of {len(TARGETS) * cc.CELLS_PER_TARGET} "
          f"({len(TARGETS)} targets x {cc.CELLS_PER_TARGET})")
    if n_cells == 0:
        sys.exit("ERROR: that directory holds no cells. Nothing to blind or score.")

TARGETS = ["claude-haiku", "claude-sonnet", "claude-opus",
           "gpt-5.5", "gpt-5.6-luna", "gpt-5.6-sol", "gpt-6-astra",
           "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash",
           "gemini-flash", "gemini-pro"]

# Pinned, never the bare "sonnet" alias. An alias resolves to whatever the CLI currently
# points at, which silently changes what a published number was measured on. This is the
# same rule the arms follow and the same one a "-latest" tag violates.
PINNED_JUDGE_MODEL = "claude-sonnet-5"

# A distinct permutation per target so position never correlates with arm.
MAPPING = {
    "claude-haiku":     {"W": ("A", 1), "X": ("B", 2), "Y": ("B", 1), "Z": ("A", 2)},
    "claude-sonnet":    {"W": ("B", 1), "X": ("A", 1), "Y": ("A", 2), "Z": ("B", 2)},
    "claude-opus":      {"W": ("A", 2), "X": ("B", 1), "Y": ("B", 2), "Z": ("A", 1)},
    "gpt-5.5":          {"W": ("B", 2), "X": ("A", 1), "Y": ("B", 1), "Z": ("A", 2)},
    "gpt-5.6-luna":     {"W": ("B", 2), "X": ("A", 2), "Y": ("A", 1), "Z": ("B", 1)},
    "gpt-5.6-sol":      {"W": ("A", 1), "X": ("B", 1), "Y": ("B", 2), "Z": ("A", 2)},
    "gpt-6-astra":      {"W": ("A", 1), "X": ("B", 1), "Y": ("A", 2), "Z": ("B", 2)},
    "gemini-3.5-flash": {"W": ("B", 1), "X": ("B", 2), "Y": ("A", 1), "Z": ("A", 2)},
    "gemini-3.6-flash": {"W": ("A", 2), "X": ("A", 1), "Y": ("B", 2), "Z": ("B", 1)},
    "gemini-3.7-flash": {"W": ("B", 2), "X": ("A", 1), "Y": ("B", 1), "Z": ("A", 2)},
    "gemini-flash":     {"W": ("B", 1), "X": ("A", 2), "Y": ("B", 2), "Z": ("A", 1)},
    "gemini-pro":       {"W": ("A", 2), "X": ("B", 2), "Y": ("A", 1), "Z": ("B", 1)},
}

# Verbatim from evals/benchmarks/README.md, committed before any run.
CHECKLIST = [
    "Gives a tri-state verdict (a three-way outcome such as VERIFIED / VERIFIED WITH GAPS / NOT VERIFIED), not a binary pass-fail and not a prose conclusion.",
    "Carries an explicit BLOCKING line stating whether the work is blocked.",
    "Carries an explicit Independence line stating whether the verification was independent of whoever produced the artifact.",
    "Ranks its defects by severity.",
    "Does not rewrite the code. It reports defects rather than handing back a corrected implementation.",
    "Gives a receipt for each axis it calls clean: how that axis was actually checked, not just an assertion that it passed.",
]

# Meta self-description only. Structural content is never stripped: in this benchmark the
# scored behaviors ARE output structure, so removing a heading would cost an arm a point it
# earned. See the small-tier run doc for the one clause-level redaction this rule required.
META = re.compile(
    r"guildproof|promptsmith|my (system )?prompt|per my instructions|as instructed|"
    r"the (prompt|instruction) file|prompt-verifier|\bAppData\b|scratchpad|"
    r"BEGIN INSTRUCTIONS|END INSTRUCTIONS|"
    r"(acting|operating|responding) as (the|a) [a-z-]+ (agent|role|specialist)|"
    r"in my role as|I have been (given|assigned|instructed)|my (assigned )?role (is|as)|"
    r"saved memory yet|what project are we working on|memory folder|session hook|startup hook|"
    r"scratch-file writes were refused|b2-run",
    re.I,
)


def blind():
    BUNDLES.mkdir(parents=True, exist_ok=True)
    rows, total_dropped = [], 0
    incomplete = []
    for tgt in TARGETS:
        parts = []
        for lab in ("W", "X", "Y", "Z"):
            arm, rep = MAPPING[tgt][lab]
            src = CELLS / f"{tgt}-{arm}{rep}.md"
            if not src.exists():
                print(f"  !! {tgt}: missing {src.name}; bundle written incomplete")
                continue
            kept, dropped = [], 0
            for line in src.read_text(encoding="utf-8").splitlines():
                if META.search(line):
                    dropped += 1
                    continue
                kept.append(line)
            total_dropped += dropped
            parts.append(f"=== OUTPUT {lab} ===\n\n" + "\n".join(kept).strip() + "\n")
            rows.append(f"{tgt},{lab},{arm},{rep}")
        (BUNDLES / f"judge-in-{tgt}.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")
        residual = sum(1 for p in parts if META.search(p))
        mark = "" if len(parts) == cc.CELLS_PER_TARGET else "  INCOMPLETE"
        if mark:
            incomplete.append(tgt)
        print(f"  {tgt}: {len(parts)} of {cc.CELLS_PER_TARGET} bundled, "
              f"residual META {residual}{mark}")
    KEY.write_text("target,label,arm,rep\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"\n{total_dropped} meta lines dropped overall")
    print(f"label key -> {KEY.name}  (never reaches a judge)")
    if incomplete:
        # An incomplete bundle still gets judged, because a partial target is better evidence
        # than none. But it must never be read as a four-cell result, so it is named here and
        # again in --tabulate rather than left for someone to notice in the counts.
        print(f"{len(incomplete)} target(s) bundled with fewer than "
              f"{cc.CELLS_PER_TARGET} cells: {', '.join(incomplete)}")
        print("  Their subtotals are out of a smaller denominator. Not a clean result.")


JUDGE_SYSTEM = """You score four unlabeled outputs against a fixed checklist and return JSON.

All four outputs answered the same user message. You do not know how any of them was
produced and must not guess. Some were produced under different conditions than others;
which is which is deliberately withheld and inferring it is not part of your job.

CHECKLIST (exactly {n} items):
{items}

SCORING RULES:
- Score only what is in the text. Never credit an output for something you believe it meant.
- Mark present ONLY with evidence. For an item requiring the output to DO something, give a
  verbatim quote. For an item requiring it to REFRAIN, set evidence_kind to "absence" and
  state exactly what you searched for and did not find.
- A vague gesture in the right direction is absent, not present. There is no partial credit.
- Length and polish are not compliance. A longer output is not more compliant.
- A strong output that satisfies an item in its own way still counts as present. You score
  the behavior, not adherence to a house style.
- Score each output separately. Never copy one output's scores onto another.

Return ONLY a JSON object, no prose before or after, no markdown fence:
{{"outputs":[{{"label":"W","scores":[{{"behavior_index":1,"present":true,"evidence_kind":"quote","evidence":"..."}}],"notable":"..."}}],"methodology_notes":"..."}}

`notable` records anything the checklist misses, including confidently wrong statements.
`methodology_notes` records where your call could reasonably have gone the other way.
"""


def run_judge(bundle_path, judge_no):
    sys_txt = JUDGE_SYSTEM.format(
        n=len(CHECKLIST),
        items="\n".join(f"{i+1}. {b}" for i, b in enumerate(CHECKLIST)),
    )
    sys_file = HERE / f"_judge_sys_{judge_no}.txt"
    sys_file.write_text(sys_txt, encoding="utf-8")

    # The bundle is PIPED IN, never read from disk by the judge. The first attempt told the
    # judge to Read the file; `claude -p` is non-interactive, so the Read hit an ungranted
    # permission prompt and every judge correctly refused to score rather than invent
    # numbers. Inlining the text also tightens the blinding: a judge with no file access
    # cannot wander into the arm outputs, the label key, or this repo.
    user = (
        f"Score every output below against every checklist item.\n"
        f"You are judge {judge_no} of 2. Another judge scores the same four outputs "
        f"independently and the two are compared, so do not hedge toward a middle. Call it "
        f"as you read it.\n"
        f"Do not use any tool. Everything you need is in this message.\n"
        f"Return only the JSON object.\n\n"
        f"{bundle_path.read_text(encoding='utf-8')}"
    )
    claude = shutil.which("claude")
    if not claude:
        return None, "claude CLI not on PATH"
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)  # shadows the subscription login
    # Prompt on stdin: a bundle can exceed the 8191-char Windows command-line limit.
    r = subprocess.run(
        [claude, "-p", "--model", PINNED_JUDGE_MODEL, "--no-session-persistence",
         "--system-prompt-file", str(sys_file)],
        input=user,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=1800, env=env,
    )
    sys_file.unlink(missing_ok=True)
    if r.returncode != 0:
        return None, f"claude exit {r.returncode}: {(r.stderr or '')[-300:]}"
    out = (r.stdout or "").strip()
    # Tolerate a fence or stray prose around the object rather than discarding the run.
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        return None, f"no JSON object in output: {out[:200]}"
    try:
        return json.loads(m.group(0)), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse failed: {e}"


def judge(only=None, force=False):
    SCORES.mkdir(parents=True, exist_ok=True)
    unfingerprinted = []
    for tgt in (only or TARGETS):
        bundle = BUNDLES / f"judge-in-{tgt}.md"
        if not bundle.exists():
            print(f"  skip {tgt}: no bundle (run --blind first)")
            continue
        bundle_bytes = bundle.read_bytes()
        for jn in (1, 2):
            dest = SCORES / f"score-{tgt}-{jn}.json"
            # The skip is load-bearing: judging 12 targets x 2 judges in one go is a long job,
            # and it has to be resumable in short foreground batches. What it must not do is
            # reuse a scorecard written against DIFFERENT bytes, which is how a re-blinded run
            # would silently report the previous run's scores.
            want = cc.bundle_fingerprint(bundle_bytes=bundle_bytes,
                                         judge_model=PINNED_JUDGE_MODEL, judge_no=jn)
            action, why = cc.reuse_verdict(dest, want)
            if force and action != "generate":
                action, why = "generate", "--force"
            if action == "reuse":
                print(f"  skip {dest.name} ({why})")
                continue
            if action == "reuse-unknown":
                print(f"  skip {dest.name} ({why})  UNFINGERPRINTED")
                unfingerprinted.append(dest.name)
                continue
            if action == "stale":
                print(f"  STALE {dest.name}: {why} -> re-judging")
            data, err = run_judge(bundle, jn)
            if err:
                print(f"  FAIL {tgt} judge{jn}: {err}")
                continue
            dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
            cc.write_sidecar(dest, want, target=tgt, judge_no=jn,
                             judge_model=PINNED_JUDGE_MODEL, bundle=bundle.name)
            n = sum(len(o.get("scores", [])) for o in data.get("outputs", []))
            print(f"  ok   {dest.name}  ({len(data.get('outputs', []))} outputs, {n} rows)")
    if unfingerprinted:
        print(f"\n{len(unfingerprinted)} reused scorecard(s) carry NO fingerprint, so nothing "
              f"here can confirm they scored the current bundles:")
        print("  " + ", ".join(unfingerprinted))
        print("  Every scorecard predating fingerprinting (added 2026-09-20) is here. "
              "--force re-judges.")


def tabulate():
    if not KEY.exists():
        sys.exit(f"ERROR: no label key at {KEY}. Run --blind first.")
    key = {}
    for line in KEY.read_text(encoding="utf-8").splitlines()[1:]:
        t, lab, arm, rep = line.split(",")
        key[(t, lab)] = (arm, int(rep))

    tal = collections.defaultdict(lambda: [0, 0])
    votes = collections.defaultdict(list)
    excluded = 0
    cards, carded, unverifiable, mismatched = 0, 0, [], []
    for f in sorted(SCORES.glob("score-*.json")):
        tgt = f.stem.replace("score-", "").rsplit("-", 1)[0]
        # Say whether each scorecard provably scored the bundle now on disk. A table that
        # cannot answer that question is a claim about a past run, not a measurement of this
        # one, and the reader is entitled to know which they are looking at.
        cards += 1
        tail = f.stem.rsplit("-", 1)[1]
        jn = int(tail) if tail.isdigit() else 0
        bundle = BUNDLES / f"judge-in-{tgt}.md"
        recorded = cc.read_fingerprint(f)
        if recorded is None:
            unverifiable.append(f.name)
        elif bundle.exists() and recorded == cc.bundle_fingerprint(
                bundle_bytes=bundle.read_bytes(),
                judge_model=PINNED_JUDGE_MODEL, judge_no=jn):
            carded += 1
        else:
            mismatched.append(f.name)
        data = json.loads(f.read_text(encoding="utf-8"))
        for o in data.get("outputs", []):
            lab = (o.get("label") or "").strip().upper()[:1]
            if (tgt, lab) not in key:
                continue
            arm, _ = key[(tgt, lab)]
            for s in o.get("scores", []):
                bi = s.get("behavior_index")
                if not isinstance(bi, int) or not (1 <= bi <= len(CHECKLIST)):
                    excluded += 1
                    continue
                tal[(tgt, bi, arm)][1] += 1
                votes[(tgt, lab, bi)].append(bool(s.get("present")))
                if s.get("present"):
                    tal[(tgt, bi, arm)][0] += 1

    print("CROSS-MODEL VERIFIER STUDY | input V-2 (subtle customer_id leak) | k=2")
    print("2 Sonnet judges per target. Cells = times PRESENT out of 4 (2 reps x 2 judges)")
    print(f"cells: {CELLS}")
    print(f"judge: {PINNED_JUDGE_MODEL} | scorecards: {cards}, "
          f"{carded} provably scored the bundles now on disk\n")
    grand = {"A": [0, 0], "B": [0, 0]}
    for tgt in TARGETS:
        sub = {"A": [0, 0], "B": [0, 0]}
        print(tgt)
        for bi in range(1, len(CHECKLIST) + 1):
            a, b = tal[(tgt, bi, "A")], tal[(tgt, bi, "B")]
            for arm, c in (("A", a), ("B", b)):
                sub[arm][0] += c[0]; sub[arm][1] += c[1]
                grand[arm][0] += c[0]; grand[arm][1] += c[1]
            short = CHECKLIST[bi - 1].split(".")[0][:44]
            print(f"   {short:46s} bare {a[0]}/{a[1]}   gp {b[0]}/{b[1]}")
        print(f"   {'subtotal':46s} bare {sub['A'][0]}/{sub['A'][1]}   gp {sub['B'][0]}/{sub['B'][1]}\n")
    ga, gb = grand["A"], grand["B"]
    if ga[1] and gb[1]:
        print(f"TOTAL  bare {ga[0]}/{ga[1]} = {100*ga[0]/ga[1]:.0f}%   "
              f"guildproof {gb[0]}/{gb[1]} = {100*gb[0]/gb[1]:.0f}%")
    n = len(votes)
    paired = {k: v for k, v in votes.items() if len(v) == 2}
    dis = sum(1 for v in paired.values() if len(set(v)) > 1)
    if paired:
        yy = sum(1 for v in paired.values() if all(v))
        nn = sum(1 for v in paired.values() if not any(v))
        m = len(paired)
        po = (yy + nn) / m
        p1 = sum(v[0] for v in paired.values()) / m
        p2 = sum(v[1] for v in paired.values()) / m
        pe = p1 * p2 + (1 - p1) * (1 - p2)
        k_ = (po - pe) / (1 - pe) if pe != 1 else float("nan")
        print(f"\ninter-judge: {m-dis}/{m} agree ({100*po:.0f}%), Cohen's kappa {k_:.2f}")
        print(f"  judge1 present-rate {p1:.2f} | judge2 {p2:.2f}")
    print(f"rows excluded as out-of-range: {excluded}")
    if unverifiable:
        print(f"\n{len(unverifiable)} scorecard(s) carry NO fingerprint. This table cannot show "
              f"that they scored the bundles now in {BUNDLES.name}/:")
        print("  " + ", ".join(unverifiable))
        print("  Every scorecard predating fingerprinting (added 2026-09-20) is in this")
        print("  category, by construction. --judge --force re-scores them.")
    if mismatched:
        print(f"\n{len(mismatched)} scorecard(s) were scored against DIFFERENT bundle bytes than "
              f"are on disk now. Re-judge them before quoting this table:")
        print("  " + ", ".join(mismatched))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--tabulate", action="store_true")
    ap.add_argument("--target", action="append",
                    help="judge only this target; repeatable. Lets judging run in short "
                         "foreground batches instead of one long background job.")
    ap.add_argument("--cells", default=cc.DEFAULT_CELLS_DIR,
                    help="directory holding the cells to score. Defaults to the same place "
                         "run-crossmodel.py writes them. Pass "
                         "evals/runs/2026-09-20-crossmodel-v2-artifacts to re-score the "
                         "committed run.")
    ap.add_argument("--force", action="store_true",
                    help="re-judge scorecards whose fingerprint already matches")
    a = ap.parse_args()
    if not (a.blind or a.judge or a.tabulate):
        ap.print_help()
        sys.exit(0)
    resolve_paths(a.cells)
    if a.blind:
        blind()
    if a.judge:
        judge(a.target, force=a.force)
    if a.tabulate:
        tabulate()
