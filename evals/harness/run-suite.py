#!/usr/bin/env python3
"""B4, numbered-case half: run the eval suite at the commit being tagged.

`evals/runner.md` describes this protocol for a human driving Claude Code interactively. That
works, and it is also why the last full-suite run is dated 2026-07-21: it takes a person an
evening, so it does not happen at every tag. This does the same thing unattended, so the gate
can actually run when it is supposed to.

Two invocations per case, both fresh OS processes:

  PRODUCER  the route's own prompt as the system prompt, the case Input as the user message.
  JUDGE     the rubric plus the case's Must / Must-not lists, the Input, and the captured
            output. It never sees the producer's context or reasoning.

The producer/judge split is not an optimisation, it is the result. `evals/rubric.md` requires an
independent judge for any case touching a security gate, a regulated output, a code artifact, an
artifact-producing route or orchestration. The first nine runs in this repo's history were
all-PASS because the thing that produced an output also graded it. Here every case gets a
separate judge, which is stricter than the rule asks for and removes the question.

Orchestration cases are NOT run by default. `/orchestrate` needs a host that can dispatch to
registered subagents, which this transport cannot do: nothing is registered, so the model would
improvise a shape that is not the product. They are reported as UNMEASURED-BY-TRANSPORT with the
reason attached, never as passing. `--include-orchestration` overrides that if you want to see
what happens, but do not put the result in a scorecard.

Usage:
    python evals/harness/run-suite.py --check                 # what it would run, spends nothing
    python evals/harness/run-suite.py --show 07                # the exact producer+judge prompts
    python evals/harness/run-suite.py --route agent            # one route, in a short batch
    python evals/harness/run-suite.py --only 07,13,21          # specific cases
    python evals/harness/run-suite.py                          # everything runnable
    python evals/harness/run-suite.py --tabulate               # scorecard from cells on disk
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
REPO = HERE.parent.parent
CASES = REPO / "evals" / "cases"
RUBRIC = REPO / "evals" / "rubric.md"

PRODUCER_MODEL = "claude-sonnet-5"
JUDGE_MODEL = "claude-sonnet-5"

# Which prompt file IS the route. Read from the shipping files, never a staged copy: a copy is a
# drift site, and the benchmark would keep measuring a stale version of the thing it tests.
ROUTE_PROMPTS = {
    "sharpen":      REPO / "skills" / "prompt-engineering" / "SKILL.md",
    "forge":        REPO / "skills" / "prompt-engineering" / "SKILL.md",
    "lens":         REPO / "skills" / "prompt-engineering" / "SKILL.md",
    "grade":        REPO / "skills" / "prompt-engineering" / "SKILL.md",
    "orchestration": REPO / "skills" / "orchestration" / "SKILL.md",
}
AGENT_ROUTES = {"agent", "gallery-agent"}
UNRUNNABLE_ROUTES = {"orchestration"}

# The command file, not the skill, carries the OUTPUT CONTRACT for a command route.
# `skills/prompt-engineering/SKILL.md:190` says so outright: "LENS -> findings list (no template;
# see /lens command)". The per-lens block layout, the ✅/⚠️/❌ finding prefixes, the worst-first
# ordering, the top-3-fixes list and the closing /guildproof:sharpen offer are all in
# `commands/lens.md:80-98` and nowhere else.
#
# Cases 05 and 06 failed their first run on exactly those four items, because this harness gave
# the producer the engine and withheld the contract it was then graded against. That is the third
# fidelity bug found in this runner, and all three had the same shape: a real user has a file that
# the transport was not handing over. When a case fails, check what the producer was actually
# given before believing the product broke.
ROUTE_COMMANDS = {
    "sharpen":       REPO / "commands" / "sharpen.md",
    "forge":         REPO / "commands" / "forge-agent.md",
    "lens":          REPO / "commands" / "lens.md",
    "grade":         REPO / "commands" / "lens.md",   # --grade is a mode of /lens, not a command
    "orchestration": REPO / "commands" / "orchestrate.md",
}

# Applied identically to every case, producer side. It exists to remove a transport artifact,
# not to tell the model how to do the work: with no plugin installed, `/guildproof:sharpen` is
# just text, and an agentic CLI left to itself goes hunting the filesystem for context instead
# of reading its prompt. That happened, cost two cells, and is why this is fixed and uniform.
PRODUCER_PREAMBLE = """Everything you need is in this message. Do not search the filesystem, do
not look for project files, and do not ask for anything. Do not call any tool: your entire reply
must be the deliverable itself, as text. The command line below names the route you are running;
your system prompt is that route's engine. Produce the real output the route is contracted to
produce, in full.

"""

# A capture that is really an apology for a tool call is not a result.
#
# Case 06's producer called ReportFindings, put its actual review inside that call, and left
# stdout holding "The review above is the real output. Please ignore the empty call." A judge then
# scored the apology and failed the case on four items, every one of them "there is no review
# here". It read exactly like the /lens route ignoring its contract.
#
# Restricting tools by flag does not work here: `--allowed-tools ""` leaves Bash, Write, Edit and
# ReportFindings available, and a `--disallowed-tools` deny list blows the context limit because
# this machine's MCP tool definitions are enormous. So the check is on the output instead, which
# does not depend on any flag's semantics. A cell that trips it is re-run once and then left
# UNSCORED rather than scored, because an unscored cell is unmeasured and not passing.
TOOL_ARTIFACT = re.compile(
    r"(?i)(ignore the (?:empty|previous) call"
    r"|the (?:review|output|answer) above is the real"
    r"|that tool call was a mistake"
    r"|apolog\w+ for the (?:empty|stray) (?:tool )?call)"
)


def looks_like_tool_artifact(text):
    """True when the captured text is a note about a tool call rather than the deliverable."""
    return bool(TOOL_ARTIFACT.search(text)) or len(text.strip()) < 200

HOOK_NOISE = re.compile(r"(?is)^.*?(?:=== VAULT RECALL.*?===.*?|Q lane:.*?$)\s*", re.MULTILINE)


def exe(name):
    """Resolve a CLI to a real path, honouring PATHEXT so Windows returns the .CMD shim."""
    return shutil.which(name)


def parse_case(path):
    """Pull the machine-readable parts out of a case file.

    Returns a dict, or raises if the shape is not what the runner expects. Raising is the point:
    a case whose headings drifted would otherwise be silently skipped or half-read, and a
    quietly-dropped case reads as a smaller suite rather than as a broken one.
    """
    text = path.read_text(encoding="utf-8")
    m = re.match(r"(?s)^---\n(.*?)\n---\n(.*)$", text)
    if not m:
        raise ValueError(f"{path.name}: no frontmatter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    body = m.group(2)

    def section(name, stop):
        sm = re.search(rf"(?m)^## {name}\s*$", body)
        if not sm:
            return None
        rest = body[sm.end():]
        em = re.search(rf"(?m)^## (?:{stop})", rest)
        return (rest[:em.start()] if em else rest).strip()

    inp = section("Input", "Must|Must not|Notes")
    # A case Input may POINT at a fixture instead of inlining it ("send the block in
    # evals/benchmarks/fixtures/x.md, verbatim"). Sending that sentence hands the model a path it
    # cannot read. Case 41 did exactly this and its verifier replied "NO VERDICT ISSUED. The
    # artifact was not in the message" -- the correct refusal, scored as four contract failures.
    # So resolve the reference and inline the file, which is what "send the block in" means.
    if inp:
        for ref in dict.fromkeys(re.findall(r"(evals/benchmarks/fixtures/[\w.-]+\.md)", inp)):
            fp = REPO / ref
            if fp.exists():
                inp += (f"\n\n===== CONTENTS OF {ref}, SENT VERBATIM =====\n"
                        f"{fp.read_text(encoding='utf-8').strip()}\n"
                        f"===== END {ref} =====")
            else:
                raise ValueError(f"{path.name}: references {ref}, which does not exist")
    must = section("Must", "Must not|Notes")
    mustnot = section("Must not", "Notes")
    if not inp:
        raise ValueError(f"{path.name}: no '## Input' section")

    return {
        "id": meta.get("id", path.name.split("-")[0]),
        "route": meta.get("route", "unknown"),
        "agent": meta.get("agent", ""),
        "tests": meta.get("tests", ""),
        "file": path.name,
        "input": inp,
        "must": must or "(none stated)",
        "mustnot": mustnot or "(none stated)",
    }


def route_prompt(case):
    """The system prompt file for this case's route, or None if the route has no runnable one."""
    if case["route"] in AGENT_ROUTES:
        if not case["agent"]:
            return None
        p = REPO / "agents" / f"{case['agent']}.md"
        return p if p.exists() else None
    return ROUTE_PROMPTS.get(case["route"])


# --- transport fidelity: give the producer the files an install would give it ----------------
# The engine resolves its lens library and its output templates from ${CLAUDE_PLUGIN_ROOT} at
# run time (skills/prompt-engineering/SKILL.md:155,184). Under `claude -p` there is no plugin
# root, so those reads fail and the model correctly says it could not load any lens.
#
# The first run of this harness scored cases 01-04 FAIL, and one of the reasons the judge gave
# was "the output disclaims loading any lenses". That is a defect in the harness, not in the
# tool: a real user installing the plugin HAS those files. Scoring the absence of the lens
# library as a product failure would have published a false result, the same way an earlier run
# nearly published "Haiku echoed the output contract" when argv mangling meant Haiku never
# received the contract.
#
# So the system prompt becomes the route prompt PLUS the lens library PLUS the templates,
# labelled as the installed files they are. This supplies the product's own content; it adds no
# instruction about how to do the work, and it is applied identically to every case.
BUNDLE_HEADER = """

---

# Installed plugin files

Everything below is the content of this plugin's install directory, which at run time is
`${CLAUDE_PLUGIN_ROOT}`. You cannot read the filesystem in this run, so the files are inlined
here instead. Treat them exactly as if you had read them from disk: the lens library below IS
the built-in lens library, and the templates below ARE the output templates your instructions
tell you to follow.

"""


def build_system_bundle(case, work_dir):
    """Concatenate the route prompt with the lens library and the output templates.

    Returns a path to write-once bundle file. Cached per route signature so 34 cases do not
    produce 34 identical multi-megabyte temp files.
    """
    base = route_prompt(case)
    if not base:
        return None
    lenses = sorted((REPO / "lenses").glob("*.md"))
    templates = sorted((REPO / "templates").glob("*.md"))

    # Bundle per route what that route actually reads at run time, not everything. Pasting all
    # twenty agent bodies into a /sharpen run would be LESS faithful than an install, not more:
    # a real host reads the gallery on demand, it does not hold it all in context. Only
    # /forge-agent is contracted to seed a new prompt from a close gallery match, so only forge
    # gets the gallery. Case 03 failed its first run for exactly this reason - the output said
    # "I could see only their one-line descriptions here, not their bodies, so I didn't adapt
    # from them", which is the harness's fault and not the engine's.
    needs_gallery = case["route"] == "forge"
    cmd_file = ROUTE_COMMANDS.get(case["route"])
    cmd_file = cmd_file if (cmd_file and cmd_file.exists()) else None

    sig = f"{base.stem}{'-' + cmd_file.stem if cmd_file else ''}{'-gallery' if needs_gallery else ''}"
    out = work_dir / f"bundle-{sig}.md"
    if out.exists():
        return out

    parts = [base.read_text(encoding="utf-8"), BUNDLE_HEADER]
    if cmd_file:
        parts.append(f"## The command you are running "
                     f"(`${{CLAUDE_PLUGIN_ROOT}}/commands/{cmd_file.name}`)\n")
        parts.append("\nThis file is the command's own definition, including its output "
                     "contract. Where it and the engine differ in detail, this file governs "
                     "the shape of what you return.\n")
        parts.append(f"\n### FILE: commands/{cmd_file.name}\n\n"
                     f"{cmd_file.read_text(encoding='utf-8')}\n")
    parts.append("## Lens library (`${CLAUDE_PLUGIN_ROOT}/lenses/`)\n")
    for p in lenses:
        parts.append(f"\n### FILE: lenses/{p.name}\n\n{p.read_text(encoding='utf-8')}\n")
    parts.append("\n## Output templates (`${CLAUDE_PLUGIN_ROOT}/templates/`)\n")
    for p in templates:
        parts.append(f"\n### FILE: templates/{p.name}\n\n{p.read_text(encoding='utf-8')}\n")
    if needs_gallery:
        parts.append("\n## Agent gallery (`${CLAUDE_PLUGIN_ROOT}/agents/`)\n")
        parts.append("\nThese are the installed gallery agents, in full. Your instructions tell "
                     "you to seed a new agent prompt from a close match here rather than build "
                     "cold; these are the bodies to adapt from.\n")
        for p in sorted((REPO / "agents").glob("*.md")):
            parts.append(f"\n### FILE: agents/{p.name}\n\n{p.read_text(encoding='utf-8')}\n")

    out.write_text("".join(parts), encoding="utf-8")
    return out


def judge_prompt(case, output, rubric):
    """The judge sees the rubric, the case's own must/must-not, the input, and the output.

    It does not see: which route file produced this, the producer's reasoning, or anything
    describing the output as good or bad.
    """
    return f"""You are an independent judge scoring ONE output against a rubric and a case
contract. You did not produce this output. Assume it is wrong and try to refute it.

The route under test is `{case['route']}`{(", agent `" + case['agent'] + "`") if case['agent'] else ""}.

===== RUBRIC =====
{rubric}
===== END RUBRIC =====

===== THE CASE INPUT =====
{case['input']}
===== END CASE INPUT =====

===== THIS CASE'S MUST LIST =====
{case['must']}
===== END MUST LIST =====

===== THIS CASE'S MUST-NOT LIST =====
{case['mustnot']}
===== END MUST-NOT LIST =====

===== THE OUTPUT TO SCORE =====
{output}
===== END OUTPUT =====

Score, in this order, quoting the output for every mark:

1. **Structural invariants** for this route from the rubric. Each one ✅ or ❌ with a one-line
   reason. Any ❌ is a hard-gate failure.
2. **Quality dimensions** for this route from the rubric. Each one ✅ / ⚠️ / ❌ with a one-line
   reason and a quote.
3. **This case's must list.** Each item ✅ or ❌.
4. **This case's must-not list.** Each item ✅ (not violated) or ❌ (violated). A violation is a
   hard-gate failure.

Apply the rubric's stance: adversarial, default to weak or fail when uncertain, make ✅ be
earned. Then apply its verdict rule, honouring hard gates: FAIL on any ❌ anywhere, WEAK if
there are ⚠️ marks but no ❌, PASS only with no ❌ and no ⚠️.

End your reply with exactly one final line, nothing after it:
VERDICT: PASS
or
VERDICT: WEAK
or
VERDICT: FAIL
"""


def run_claude(model, system_path, user_text, timeout=900):
    """One call, one fresh process.

    The prompt goes on STDIN. It must never go on argv: on Windows `claude` resolves to a .CMD
    batch shim and cmd.exe re-parses the arguments, which silently mangled prompts containing
    SQL and backticks. The command line also caps at 8191 characters and these prompts are far
    past it. encoding/errors are explicit because text=True alone decodes with the Windows ANSI
    codepage, where one em-dash in model output crashes the reader thread and leaves stdout as
    None, surfacing as an AttributeError nowhere near the cause.
    """
    claude = exe("claude")
    if not claude:
        raise SystemExit("claude CLI not on PATH (npm i -g @anthropic-ai/claude-code)")
    cmd = [claude, "-p", "--model", model, "--no-session-persistence"]
    if system_path:
        cmd += ["--system-prompt-file", str(system_path)]
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)   # shadows the subscription login even with no credits
    r = subprocess.run(cmd, input=user_text, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, env=env)
    out = (r.stdout or "").strip()
    if not out:
        raise RuntimeError(f"empty output (exit {r.returncode}): {(r.stderr or '')[:400]}")
    return out


def parse_verdict(raw):
    cleaned = HOOK_NOISE.sub("", raw).strip()
    hits = re.findall(r"(?mi)^\s*\**VERDICT:\**\s*\**(PASS|WEAK|FAIL)\**", cleaned)
    return (hits[-1].upper() if hits else None), cleaned


def load_cases(args):
    cases = []
    for p in sorted(CASES.glob("*.md")):
        c = parse_case(p)
        if args.only and c["id"] not in {x.strip() for x in args.only.split(",")}:
            continue
        if args.route and c["route"] != args.route:
            continue
        cases.append(c)
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--show", metavar="ID")
    ap.add_argument("--only", metavar="IDS")
    ap.add_argument("--route", metavar="ROUTE")
    ap.add_argument("--include-orchestration", action="store_true")
    ap.add_argument("--tabulate", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    rubric = RUBRIC.read_text(encoding="utf-8")
    out_dir = pathlib.Path(args.out) if args.out else (
        REPO / "evals" / "runs" / "2026-09-20-b4-suite-artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "_bundles").mkdir(exist_ok=True)

    cases = load_cases(args)
    if not cases:
        raise SystemExit("no cases matched")

    if args.check:
        print(f"cases parsed : {len(cases)}")
        print(f"rubric       : {RUBRIC} ({len(rubric.splitlines())} lines)")
        print(f"producer     : {PRODUCER_MODEL} (pinned)   judge: {JUDGE_MODEL} (pinned)")
        print(f"claude CLI   : {exe('claude') or 'NOT ON PATH - npm i -g @anthropic-ai/claude-code'}")
        runnable = 0
        for c in cases:
            sp = route_prompt(c)
            if c["route"] in UNRUNNABLE_ROUTES and not args.include_orchestration:
                print(f"  {c['id']:>3} {c['route']:<14} UNMEASURED-BY-TRANSPORT "
                      f"(needs a host that can dispatch registered subagents)")
            elif not sp:
                print(f"  {c['id']:>3} {c['route']:<14} NO PROMPT RESOLVED "
                      f"(agent={c['agent'] or 'none'})")
            else:
                runnable += 1
                print(f"  {c['id']:>3} {c['route']:<14} -> {sp.relative_to(REPO)}")
        print(f"\n{runnable} runnable, {len(cases) - runnable} not. "
              f"{runnable * 2} calls ({runnable} producer + {runnable} judge).")
        raise SystemExit(0)

    if args.show:
        c = next((x for x in cases if x["id"] == args.show), None)
        if not c:
            raise SystemExit(f"no case {args.show}")
        sp = route_prompt(c)
        print(f"### PRODUCER system prompt file: {sp}")
        print(f"### PRODUCER user message:\n{PRODUCER_PREAMBLE}{c['input']}")
        print(f"\n### JUDGE prompt:\n{judge_prompt(c, '<the captured output>', rubric)}")
        raise SystemExit(0)

    results = []
    for c in cases:
        cid = c["id"]
        sp = route_prompt(c)
        if c["route"] in UNRUNNABLE_ROUTES and not args.include_orchestration:
            results.append({"id": cid, "route": c["route"], "verdict": "UNMEASURED-BY-TRANSPORT",
                            "why": "needs a host that can dispatch registered subagents"})
            print(f"{cid}: UNMEASURED-BY-TRANSPORT")
            continue
        if not sp:
            results.append({"id": cid, "route": c["route"], "verdict": "UNMEASURED",
                            "why": f"no prompt file resolved for agent={c['agent'] or 'none'}"})
            print(f"{cid}: UNMEASURED (no prompt resolved)")
            continue

        out_cell = out_dir / f"case-{cid}-output.md"
        judge_cell = out_dir / f"case-{cid}-judge.md"

        if not args.tabulate:
            if not out_cell.exists():
                print(f"{cid}: producing...", flush=True)
                try:
                    bundle = build_system_bundle(c, out_dir / "_bundles")
                    out = run_claude(PRODUCER_MODEL, bundle, PRODUCER_PREAMBLE + c["input"])
                    if looks_like_tool_artifact(HOOK_NOISE.sub("", out)):
                        print(f"{cid}: capture looks like a tool-call artifact, retrying once",
                              flush=True)
                        out = run_claude(PRODUCER_MODEL, bundle, PRODUCER_PREAMBLE + c["input"])
                        if looks_like_tool_artifact(HOOK_NOISE.sub("", out)):
                            raise RuntimeError(
                                "producer output is a tool-call artifact twice, not a deliverable")
                except Exception as e:
                    print(f"{cid}: PRODUCER ERROR {e}")
                    results.append({"id": cid, "route": c["route"], "verdict": None,
                                    "why": f"producer error: {e}"})
                    continue
                out_cell.write_text(HOOK_NOISE.sub("", out).strip(), encoding="utf-8")
            if not judge_cell.exists():
                print(f"{cid}: judging...", flush=True)
                try:
                    raw = run_claude(JUDGE_MODEL, None,
                                     judge_prompt(c, out_cell.read_text(encoding="utf-8"), rubric))
                except Exception as e:
                    print(f"{cid}: JUDGE ERROR {e}")
                    results.append({"id": cid, "route": c["route"], "verdict": None,
                                    "why": f"judge error: {e}"})
                    continue
                v, cleaned = parse_verdict(raw)
                judge_cell.write_text(cleaned, encoding="utf-8")

        if judge_cell.exists():
            v, _ = parse_verdict(judge_cell.read_text(encoding="utf-8"))
            results.append({"id": cid, "route": c["route"], "verdict": v})
            print(f"{cid}: {v}")

    # --- tabulate -------------------------------------------------------------------------
    try:
        ref = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                             text=True, encoding="utf-8", errors="replace").stdout.strip()
    except Exception:
        ref = "unknown"

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    print("\n=== B4, numbered cases ===")
    print(f"commit under test : {ref}")
    print(f"producer / judge  : {PRODUCER_MODEL} / {JUDGE_MODEL}, separate processes")
    for k in ("PASS", "WEAK", "FAIL", None, "UNMEASURED", "UNMEASURED-BY-TRANSPORT"):
        if k in counts:
            print(f"  {str(k):<26} {counts[k]}")
    fails = [r["id"] for r in results if r["verdict"] == "FAIL"]
    weaks = [r["id"] for r in results if r["verdict"] == "WEAK"]
    unscored = [r["id"] for r in results if r["verdict"] is None]
    if fails:
        print(f"\nFAIL: {', '.join(fails)}")
    if weaks:
        print(f"WEAK: {', '.join(weaks)}")
    if unscored:
        print(f"UNSCORED (an unscored case is unmeasured, not passing): {', '.join(unscored)}")

    summary = {"benchmark": "B4-suite", "commit": ref, "producer_model": PRODUCER_MODEL,
               "judge_model": JUDGE_MODEL, "counts": {str(k): v for k, v in counts.items()},
               "cases": results}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nartifacts: {out_dir}")
    # The gate is no FAIL and nothing unscored. WEAK is a finding to fix, not a blocker.
    sys.exit(1 if (fails or unscored) else 0)


if __name__ == "__main__":
    main()
