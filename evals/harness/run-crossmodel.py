"""Generate the cross-model verifier arms, each in a process that cannot see this session.

WHY THIS REPLACES THE WORKFLOW HARNESS
--------------------------------------
The first V-2 attempt ran its arms as Claude Code workflow subagents. That harness relays
the parent conversation's most recent user message to every subagent, on every model. Two
of eight bare-arm cells received a user question about publishing results and answered it
instead of only verifying the artifact, which depressed the bare arm and would have
inflated the measured gap. A probe confirmed the mechanism and confirmed it is independent
of the model override.

Every transport below is a fresh OS process with no channel to this conversation, verified
by asking each one what context it could see:

  claude -p   "No prior conversation history - this is the first user message."
  codex exec  "no"
  gemini REST "You did not provide any context."

So blinding here is a property of the transport, not a rule a harness is asked to respect.

ONE TRANSPORT ASYMMETRY, DISCLOSED
----------------------------------
Claude and Gemini accept a real system prompt (--system-prompt-file, systemInstruction).
Codex exec has no system-prompt flag, so for the GPT arm the specialist prompt is prepended
to the user message behind an explicit delimiter. That is a weaker form of the same
instruction and it is recorded here rather than smoothed over.

Usage:
    python run-crossmodel.py --input evals/benchmarks/fixtures/v2-invoice-subtle.md
    python run-crossmodel.py --input ... --outdir ... --only gemini-pro   (one target)
    python run-crossmodel.py --probe                                     (isolation check only)

The default output directory and the fingerprint format both live in `crossmodel_cells.py`,
which `judge-crossmodel.py` imports as well. They used to be two separate literals that
disagreed, so the published reproduce sequence generated cells here and scored different ones
elsewhere. That module's docstring has the detail.
"""

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

import crossmodel_cells as cc


def exe(name):
    """Resolve a CLI to a real executable path, or None if it is not installed.

    On Windows npm installs both a POSIX shell script (`claude`) and a `.CMD` shim, and
    CreateProcess can only launch the latter. shutil.which honours PATHEXT and returns
    the .CMD, so this avoids a WinError 2 that otherwise looks like "not installed".

    Returns None rather than exiting: a machine missing one vendor's CLI should skip that
    target and still produce the others. A harness that only runs on its author's laptop
    is a demo, not evidence.
    """
    return shutil.which(name)


def availability(env, targets):
    """Report which targets this machine can actually run, and why not for the rest.

    Every reason is a checked fact, not a guess: the CLI is resolved on PATH, the login is
    queried, the key is read from the environment. Nothing here spends a token.

    `targets` comes from the run manifest, so this reports on the roster the run declares
    rather than on a list this file happens to carry.
    """
    rows = {}
    claude_path = exe("claude")
    codex_path = exe("codex")

    claude_why = None
    if not claude_path:
        claude_why = "claude CLI not on PATH (npm i -g @anthropic-ai/claude-code)"
    elif os.environ.get("ANTHROPIC_API_KEY"):
        # Not fatal: the runner strips it per call. Worth surfacing because it silently
        # shadows a subscription login and produced a "Credit balance is too low" error
        # that looks like an account problem rather than an env problem.
        claude_why = None

    codex_why = None
    if not codex_path:
        codex_why = "codex CLI not on PATH (npm i -g @openai/codex)"
    else:
        r = subprocess.run([codex_path, "login", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if r.returncode != 0 or "logged in" not in (r.stdout + r.stderr).lower():
            codex_why = "codex is installed but not logged in (run: codex login)"

    gem_why = None
    if not (env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")):
        gem_why = "no GEMINI_API_KEY (get one at aistudio.google.com/apikey)"

    for t in targets:
        why = {"claude": claude_why, "codex": codex_why, "gemini": gem_why}.get(
            t["transport"], f"unknown transport {t['transport']!r}")
        rows[t["key"]] = (why is None, why)
    return rows

HERE = pathlib.Path(__file__).parent
REPO = HERE.parent.parent                      # evals/harness -> evals -> repo root
GEMINI_CALLER = HERE / "gemini-call.py"

# Defaults used only when WRITING a new manifest. The manifest records them as repo-relative
# paths, and from then on the run reads its own manifest. The specialist prompt is always read
# from the shipping file, never a staged copy: a copy is a drift site, and the benchmark would
# keep measuring a stale version of the prompt it claims to test.
DEFAULT_SYSTEM_PROMPT = "agents/verifier.md"
DEFAULT_REPS = 2
DEFAULT_JUDGE_MODEL = "claude-sonnet-5"
DEFAULT_JUDGES_PER_TARGET = 2

# The SHIPPED DEFAULT roster, used only to write a new run.json. It is not the definition of
# any run: once a manifest exists, the manifest's roster is what runs, and this list is unused.
#
# It is also this author's model access, which nobody else has. Cut it down with
# `--targets claude-opus,gemini-pro`, or write your own run.json — a run with two targets is
# a smaller claim than one with twelve, and a real one.
#
# Exact model ids, pinned. Never a "-latest" alias: an alias silently changes what a
# published number was measured on.
SHIPPED_TARGETS = [
    {"key": "claude-haiku", "transport": "claude", "model": "claude-haiku-4-5-20251001", "family": "Claude", "tier": "small"},
    {"key": "claude-sonnet", "transport": "claude", "model": "claude-sonnet-5", "family": "Claude", "tier": "mid"},
    {"key": "claude-opus", "transport": "claude", "model": "claude-opus-5", "family": "Claude", "tier": "frontier"},
    # OpenAI is a 3-generation ladder, 5.5 -> 5.6 -> 6, with TWO sibling variants at 5.6.
    # luna vs sol is a within-generation control: two siblings should score alike, and if
    # they do not, the measurement is noisier than the report claims.
    {"key": "gpt-5.5", "transport": "codex", "model": "gpt-5.5", "family": "OpenAI", "tier": "gen-5.5"},
    {"key": "gpt-5.6-luna", "transport": "codex", "model": "gpt-5.6-luna", "family": "OpenAI", "tier": "gen-5.6"},
    {"key": "gpt-5.6-sol", "transport": "codex", "model": "gpt-5.6-sol", "family": "OpenAI", "tier": "gen-5.6"},
    {"key": "gpt-6-astra", "transport": "codex", "model": "gpt-6-astra", "family": "OpenAI", "tier": "gen-6"},
    # Google gives a clean GENERATION ladder at a constant tier: 3.5 (May 2026) through
    # 3.8, flash throughout. That isolates capability from tier, which a pro-vs-flash
    # comparison cannot. 3.1-pro is kept as the one older-but-larger data point: there is
    # no pro newer than 3.1 on this key, so "frontier" is not well defined across the grid
    # and the tier label is deliberately not used for Google.
    {"key": "gemini-3.5-flash", "transport": "gemini", "model": "gemini-3.5-flash", "family": "Google", "tier": "gen-3.5"},
    {"key": "gemini-3.6-flash", "transport": "gemini", "model": "gemini-3.6-flash", "family": "Google", "tier": "gen-3.6"},
    {"key": "gemini-3.7-flash", "transport": "gemini", "model": "gemini-3.7-flash", "family": "Google", "tier": "gen-3.7"},
    {"key": "gemini-flash", "transport": "gemini", "model": "gemini-3.8-flash", "family": "Google", "tier": "gen-3.8"},
    {"key": "gemini-pro", "transport": "gemini", "model": "gemini-3.1-pro-preview", "family": "Google", "tier": "gen-3.1-pro"},
]

REPS = [1, 2]


def gemini_env():
    """Read the key from the persisted User scope, because this process may predate it.

    The value is passed to the child process only. It is never printed or logged.
    """
    env = dict(os.environ)
    if not env.get("GEMINI_API_KEY"):
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 '[Environment]::GetEnvironmentVariable("GEMINI_API_KEY","User")'],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
            val = out.stdout.strip()
            if val:
                env["GEMINI_API_KEY"] = val
        except Exception:
            pass
    return env


def run_claude(model, system_path, user_text, out_path):
    """Run one Claude arm, prompt on STDIN.

    The prompt must NOT go on argv. On Windows `claude` resolves to a .CMD batch shim, and
    cmd.exe re-parses its arguments: a multi-line prompt containing SQL, backticks, braces
    and % or & characters arrives mangled. The symptom was not an error. The model received
    a fragment, replied "your message is terse and I don't have context", and one cell even
    captured an interactive "this directory has no saved memory yet" prompt. Four cells read
    as a model failing to verify when in fact the artifact never reached it.
    """
    cmd = [exe("claude"), "-p", "--model", model, "--no-session-persistence"]
    if system_path:
        cmd += ["--system-prompt-file", str(system_path)]
    env = dict(os.environ)
    # A credit-less ANTHROPIC_API_KEY shadows the subscription login and makes this fail.
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(cmd, input=user_text, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, env=env)
    if r.returncode != 0:
        return None, f"claude exit {r.returncode}: {(r.stderr or '')[-400:]}"
    text = (r.stdout or "").strip()
    return (text, None) if text else (None, "claude returned empty stdout")


# codex exec is an AGENTIC cli, not a bare chat endpoint: its default posture is to go
# explore a workspace. On the first run that produced garbage for the GPT bare arm, which
# replied "the environment's execution policy blocked read-only file discovery... please
# paste the artifact" about an artifact that was already in its prompt. This preamble makes
# the task equivalent to the one the other transports get. It is applied to BOTH arms,
# identically, so it cannot advantage either side; it removes a harness artifact rather than
# adding an instruction about how to do the work.
CODEX_SELF_CONTAINED = (
    "Everything you need is in this message. Do not read files, list directories, run "
    "commands, or search the workspace: there is nothing there for this task. Answer "
    "directly from the text below.\n\n"
)


def run_codex(model, system_path, user_text, out_path):
    if system_path:
        prompt = (
            CODEX_SELF_CONTAINED
            + "Your operating instructions are the entire text between the INSTRUCTIONS "
            "markers. Adopt them completely: they define your role, your method and the "
            "shape of your output.\n\n"
            "=== BEGIN INSTRUCTIONS ===\n"
            + system_path.read_text(encoding="utf-8")
            + "\n=== END INSTRUCTIONS ===\n\n"
            "Now answer the following message in that role.\n\n" + user_text
        )
    else:
        prompt = CODEX_SELF_CONTAINED + user_text
    # The prompt goes in on STDIN, not argv. Windows caps a command line at 8191 chars and
    # the verifier prompt alone is ~7700, so passing it as an argument failed with "The
    # command line is too long" and lost both GPT arm-B cells.
    cmd = [
        exe("codex"), "exec",
        "-m", model,            # pinned; the CLI default silently changes the arm
        "--sandbox", "read-only",
        "--skip-git-repo-check",
        "--ephemeral",          # no saved session
        "--ignore-user-config", # no ~/.codex config
        "--ignore-rules",       # no AGENTS.md picked up from disk
    ]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    if r.returncode != 0:
        return None, f"codex exit {r.returncode}: {(r.stderr or '')[-400:]}"
    # codex exec prints a banner, then the turn. Keep everything after the last "codex"
    # role marker, and fall back to the whole stdout if the marker shape changes.
    out = r.stdout or ""
    marker = "\ncodex\n"
    body = out.rsplit(marker, 1)[-1] if marker in out else out
    # Drop the trailing token-usage footer if present.
    for cut in ("\ntokens used\n", "\ntokens used"):
        if cut in body:
            body = body.split(cut)[0]
    body = body.strip()
    return (body, None) if body else (None, "codex returned empty body")


def run_gemini(model, system_path, user_path, out_path, env):
    cmd = [sys.executable, str(GEMINI_CALLER), "--model", model,
           "--user", str(user_path), "--out", str(out_path)]
    if system_path:
        cmd += ["--system", str(system_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, env=env)
    if r.returncode != 0:
        return None, f"gemini exit {r.returncode}: {(r.stdout + r.stderr)[-400:]}"
    return out_path.read_text(encoding="utf-8").strip(), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="file holding the user message, sent verbatim to every arm")
    ap.add_argument("--outdir", default=cc.DEFAULT_CELLS_DIR,
                    help="where cells are written. The default is shared with "
                         "judge-crossmodel.py's --cells, so the published sequence scores the "
                         "cells it just generated instead of the committed historical ones.")
    ap.add_argument("--targets",
                    help="comma-separated target keys for a NEW run, e.g. "
                         "'claude-opus,gemini-pro'. The shipped roster is this author's model "
                         "access; yours will differ. Ignored once run.json exists — edit that.")
    ap.add_argument("--run-id", help="names a new run; defaults to the output directory name")
    ap.add_argument("--seed", help="blinding seed for a new run; defaults to the run id")
    ap.add_argument("--only", help="run a single target key")
    ap.add_argument("--transport", choices=["claude", "codex", "gemini"],
                    help="run only targets on one transport. Useful when memory is tight: a "
                         "gemini cell is an HTTPS call (~30 MB) while a claude cell spawns a "
                         "whole Claude Code process (~500 MB).")
    ap.add_argument("--probe", action="store_true", help="isolation probe only, no eval")
    ap.add_argument("--check", action="store_true",
                    help="report which targets this machine can run, then exit. Spends nothing.")
    ap.add_argument("--dry-run", action="store_true",
                    help="print every call that would be made, without making any of them")
    ap.add_argument("--force", action="store_true",
                    help="regenerate every requested cell even when its fingerprint still "
                         "matches. Rarely needed: a cell whose inputs changed regenerates on "
                         "its own.")
    a = ap.parse_args()

    env = gemini_env()
    outdir = cc.resolve_cells_dir(HERE, a.outdir)

    # THE MANIFEST DECIDES WHAT THIS RUN IS. If one exists it wins outright, including over a
    # conflicting flag, because silently re-pointing an existing run at a different input is
    # precisely how cells from two different stimuli end up in one directory being scored as
    # one result. A conflicting flag is reported, not applied.
    manifest = cc.read_manifest(outdir)
    if manifest:
        print(f"run: {manifest['run_id']}  (manifest: {cc.manifest_path(outdir)})")
        for flag, val, field in (("--input", a.input, "input"),
                                 ("--targets", a.targets, None)):
            if not val:
                continue
            current = ", ".join(t["key"] for t in manifest["targets"]) if field is None \
                else manifest[field]
            if str(val) != str(current):
                print(f"  IGNORING {flag}: this run already declares {current!r}. "
                      f"Edit {cc.MANIFEST_NAME} to change it, or use a new --outdir.")
    else:
        if not a.input and not (a.check or a.probe):
            sys.exit("ERROR: --input is required to start a new run (it becomes run.json).")
        roster = SHIPPED_TARGETS
        if a.targets:
            want = [k.strip() for k in a.targets.split(",") if k.strip()]
            known = {t["key"] for t in SHIPPED_TARGETS}
            unknown = [k for k in want if k not in known]
            if unknown:
                sys.exit(f"ERROR: unknown target key(s) {unknown}. Known: "
                         f"{sorted(known)}. Or write your own {cc.MANIFEST_NAME}.")
            roster = [t for t in SHIPPED_TARGETS if t["key"] in want]
        run_id = a.run_id or outdir.name
        manifest = {
            "schema": cc.SCHEMA,
            "run_id": run_id,
            "input": a.input or "",
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "reps": DEFAULT_REPS,
            "judge_model": DEFAULT_JUDGE_MODEL,
            "judges_per_target": DEFAULT_JUDGES_PER_TARGET,
            "checklist_source": "evals/benchmarks/README.md, committed before any run",
            "checklist": cc.DEFAULT_CHECKLIST,
            "targets": roster,
            "labels": {"seed": a.seed or run_id},
        }
        # Not written to disk yet: --check and --dry-run must not create a run directory as a
        # side effect of asking a question. It is written once real work begins.
        print(f"run: {run_id}  (new; {cc.MANIFEST_NAME} written when the first cell runs)")

    all_targets = manifest["targets"]
    reps = list(range(1, manifest["reps"] + 1))
    arms = cc.arms_for(manifest)

    targets = [t for t in all_targets
               if (not a.only or t["key"] == a.only)
               and (not a.transport or t["transport"] == a.transport)]

    avail = availability(env, all_targets)
    print("Targets on this machine:")
    for t in all_targets:
        ok, why = avail[t["key"]]
        mark = "RUNNABLE" if ok else "SKIP    "
        print(f"  {mark}  {t['key']:15s} {t['family']:7s} {t['model'] or '(codex default)'}")
        if why:
            print(f"            reason: {why}")
    runnable = [t for t in targets if avail[t["key"]][0]]
    skipped = [t for t in targets if not avail[t["key"]][0]]
    if skipped:
        # Never let a skipped vendor read as a measured result. Say it out loud, twice:
        # here and again in the manifest.
        print(f"\n{len(skipped)} target(s) skipped. Their cells are UNMEASURED, not clean.")
    if a.check:
        # --check IS the setup documentation. A prose prerequisites list goes stale the
        # moment a vendor renames a flag; this reads the machine, so it cannot.
        if skipped:
            print("\nFix the reasons above, then run --check again. Partial setup is fine:")
            print("every target that works still produces evidence, and the rest are")
            print("recorded as unmeasured rather than quietly dropped.")
        else:
            print("\nAll targets runnable. Next:")
            print("  1. python run-crossmodel.py --dry-run --input <file>   see every call, spend nothing")
            print("  2. python run-crossmodel.py --probe                    confirm each model is isolated")
            print("  3. python run-crossmodel.py --input <file>             run it")
        print("\nNote: steps 2 and 3 spend your own subscription quota and API credits.")
        return

    # --dry-run is deliberately ABOVE the runnable gate. On a machine with no credentials
    # every target skips, and that is exactly when someone most wants to see what this
    # would do before setting anything up. Gating it behind "you must already be set up"
    # broke the first command a new user would reach for.
    if a.dry_run:
        # Print the exact shape of every call without making any of them, so a new user can
        # see what this is about to do to their quota before it does it.
        if not manifest["input"]:
            sys.exit("ERROR: --dry-run still needs --input, so the plan reflects the real run")
        # Plan every REQUESTED target, not only the runnable ones. A new user with nothing
        # set up still needs to see the whole shape of the run before deciding to set it up.
        plan = [x for x in all_targets if not a.only or x["key"] == a.only]
        n = len(plan) * len(arms) * len(reps)
        print(f"\nDRY RUN. {n} calls would be made ({len(plan)} targets x {len(arms)} arms "
              f"x k={len(reps)}).")
        print(f"Input sent verbatim to every arm: {manifest['input']}")
        for arm in arms:
            sp = arm.get("system_prompt") or "no system prompt (bare)"
            print(f"  arm {arm['id']}: {arm.get('label', '?')} -> {sp}")
        for t in plan:
            sysnote = {
                "claude": "--system-prompt-file",
                "gemini": "systemInstruction field",
                "codex": "PREPENDED to the user message (codex exec has no system-prompt flag)",
            }[t["transport"]]
            print(f"\n  {t['key']}  ({t['family']}, {t['model'] or 'codex default'})")
            print(f"    transport   : {t['transport']}")
            print(f"    arm B via   : {sysnote}")
            ids = ",".join(x["id"] for x in arms)
            print(f"    would write : {a.outdir}/{t['key']}-{{{ids}}}{{1..{len(reps)}}}.md")
        if skipped:
            print(f"\n  {len(skipped)} of these would SKIP on this machine for lack of credentials.")
            print("  Run --check for the exact reason and fix for each.")
        print("\nNothing was called and nothing was written.")
        return

    if not runnable:
        sys.exit("ERROR: no runnable targets. Run --check for the reasons and how to fix each.")
    targets = runnable

    if a.probe:
        q = ("Without using any tool, answer in under 40 words: can you see any conversation "
             "about a project called guildproof, any eval benchmark, or any user message about "
             "API keys? Yes or no, then name the context you were given.")
        for t in targets:
            if t["transport"] == "claude":
                txt, err = run_claude(t["model"], None, q, None)
            elif t["transport"] == "codex":
                txt, err = run_codex(t["model"], None, q, None)
            else:
                tmp = HERE / "_probe.txt"; tmp.write_text(q, encoding="utf-8")
                txt, err = run_gemini(t["model"], None, tmp, HERE / "_probe.out", env)
            print(f"\n--- {t['key']} ---")
            print(err if err else txt[:400])
        return

    if not manifest["input"]:
        sys.exit("ERROR: --input is required")

    # Resolve and read every arm's system prompt up front. A missing one must stop the run, not
    # silently turn that arm bare: a bare arm mislabelled as a prompted one reads as a null
    # finding about the prompt, which is the most expensive kind of wrong result here.
    arm_bytes, arm_paths = {}, {}
    for arm in arms:
        if not arm.get("system_prompt"):
            arm_bytes[arm["id"]], arm_paths[arm["id"]] = None, None
            continue
        p = cc.resolve_repo_path(HERE, arm["system_prompt"])
        if not p.exists():
            sys.exit(f"ERROR: arm {arm['id']} ({arm.get('label', '?')}) names system prompt "
                     f"{arm['system_prompt']!r}, which is not at {p}. Refusing to run: that arm "
                     f"would go out bare and the result would read as a null finding.")
        arm_paths[arm["id"]], arm_bytes[arm["id"]] = p, p.read_bytes()

    user_path = cc.resolve_repo_path(HERE, manifest["input"])
    if not user_path.exists():
        sys.exit(f"ERROR: input not found at {user_path} "
                 f"(manifest says {manifest['input']!r}).")
    user_text = user_path.read_text(encoding="utf-8")
    # Hash the bytes on disk, not the decoded string: the fingerprint has to notice a change
    # that only shows up in the encoding, and the prompt files are read as bytes for the same
    # reason on the other side.
    input_bytes = user_path.read_bytes()

    outdir.mkdir(parents=True, exist_ok=True)
    # Real work is starting, so the run's definition goes to disk now. From here the judge
    # reads its roster, reps, judge model, checklist and blinding from this file, which is why
    # the two halves can no longer disagree about what the run is.
    cc.write_manifest(outdir, manifest)
    # Print the resolved directory and the matching judge command. The whole defect this
    # replaces was invisible precisely because neither half ever said which directory it used.
    print(f"\ncells dir: {outdir}")
    print(f"manifest : {cc.manifest_path(outdir).name}  "
          f"({len(all_targets)} targets, k={len(reps)}, judge {manifest['judge_model']})")
    if a.outdir == cc.DEFAULT_CELLS_DIR:
        print("score these with: python judge-crossmodel.py --blind    (same default dir)")
    else:
        print(f"score these with: python judge-crossmodel.py --blind --cells {a.outdir}")

    cell_log = []
    unfingerprinted = []
    for t in targets:
        for arm_def in arms:
            arm = arm_def["id"]
            for rep in reps:
                name = f"{t['key']}-{arm}{rep}.md"
                out_path = outdir / name
                fp = cc.cell_fingerprint(
                    input_bytes=input_bytes,
                    system_bytes=arm_bytes[arm],
                    model=t["model"], transport=t["transport"], arm=arm, rep=rep,
                )

                # A cell already on disk is not re-run, because a sweep that dies mid-way (the
                # first attempt died on a cp1252 decode after 6 of 16 cells) must not re-spend
                # the whole quota. But reuse is now conditional on the inputs still hashing the
                # same, so a reworded verifier.md or a different fixture cannot be silently
                # scored as if it were the measured one.
                action, why = cc.reuse_verdict(out_path, fp)
                if a.force and action != "generate":
                    action, why = "generate", "--force"
                if action in ("reuse", "reuse-unknown"):
                    flag = "" if action == "reuse" else "  UNFINGERPRINTED"
                    print(f"  skip {name}  ({why}){flag}")
                    if action == "reuse-unknown":
                        unfingerprinted.append(name)
                    cell_log.append({**t, "arm": arm, "rep": rep, "file": name,
                                    "ok": True, "reused": True,
                                     "fingerprint": fp if action == "reuse" else None,
                                     "fingerprint_status": action,
                                     "chars": len(out_path.read_text(encoding="utf-8"))})
                    continue
                if action == "stale":
                    print(f"  STALE {name}: {why} -> regenerating")

                sysp = arm_paths[arm]
                t0 = time.time()
                if t["transport"] == "claude":
                    txt, err = run_claude(t["model"], sysp, user_text, out_path)
                elif t["transport"] == "codex":
                    txt, err = run_codex(t["model"], sysp, user_text, out_path)
                else:
                    txt, err = run_gemini(t["model"], sysp, user_path, out_path, env)

                if err:
                    print(f"  FAIL {name}: {err}")
                    cell_log.append({**t, "arm": arm, "rep": rep, "file": name,
                                     "ok": False, "error": err})
                    continue
                # Write unconditionally. This used to read `if txt and not out_path.exists()`,
                # which made --force worse than a no-op: it spent the call, got the new answer,
                # then kept the old file. The guard existed because the gemini transport writes
                # out_path itself; rewriting the same text it just returned is harmless.
                if txt:
                    out_path.write_text(txt + "\n", encoding="utf-8")
                    cc.write_sidecar(
                        out_path, fp,
                        model=t["model"], transport=t["transport"], arm=arm, rep=rep,
                        input_file=str(user_path),
                        system_prompt=arm_def.get("system_prompt"),
                        arm_label=arm_def.get("label"),
                    )
                print(f"  ok   {name}  ({len(txt)} chars, {time.time()-t0:.0f}s)")
                cell_log.append({**t, "arm": arm, "rep": rep, "file": name,
                                 "ok": True, "fingerprint": fp,
                                 "fingerprint_status": "fresh", "chars": len(txt)})

    # MERGE the per-cell log rather than overwriting it. This used to be a plain overwrite, so
    # a run taken in batches (`--transport codex`, then gemini, then claude) left a file
    # describing only the LAST batch: the committed 2026-09-20 run's log lists 16 of its 48
    # cells. A record that silently shrinks to the last invocation is not a record of the run.
    log_path = outdir / "cells.json"
    merged = {}
    for source in (outdir / "manifest.json", log_path):
        if source.exists():
            try:
                for row in json.loads(source.read_text(encoding="utf-8")):
                    merged[row["file"]] = row
            except (json.JSONDecodeError, KeyError, TypeError):
                print(f"  note: {source.name} was unreadable; rebuilding from this invocation")
    for row in cell_log:
        merged[row["file"]] = row
    rows = [merged[k] for k in sorted(merged)]
    log_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    ok = sum(1 for m in cell_log if m["ok"])
    print(f"\n{ok} of {len(cell_log)} cells produced output this invocation. "
          f"Failures are unmeasured, not clean.")
    print(f"{len(rows)} of {len(all_targets) * len(arms) * len(reps)} cells recorded in "
          f"{log_path.name} across all invocations.")
    if unfingerprinted:
        print(f"{len(unfingerprinted)} reused cell(s) carry NO fingerprint, so nothing here can "
              f"confirm which inputs produced them:")
        print("  " + ", ".join(unfingerprinted))
        print("  Every cell predating fingerprinting (added 2026-09-20) is here. "
              "--force regenerates.")


if __name__ == "__main__":
    main()
