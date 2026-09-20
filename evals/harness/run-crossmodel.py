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
    python run-crossmodel.py --input inputs/v2-invoice-subtle.md --outdir out-crossmodel
    python run-crossmodel.py --input ... --outdir ... --only gemini-pro   (one target)
    python run-crossmodel.py --probe                                     (isolation check only)
"""

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time


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


def availability(env):
    """Report which targets this machine can actually run, and why not for the rest.

    Every reason is a checked fact, not a guess: the CLI is resolved on PATH, the login is
    queried, the key is read from the environment. Nothing here spends a token.
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

    for t in TARGETS:
        why = {"claude": claude_why, "codex": codex_why, "gemini": gem_why}[t["transport"]]
        rows[t["key"]] = (why is None, why)
    return rows

HERE = pathlib.Path(__file__).parent
REPO = HERE.parent.parent                      # evals/harness -> evals -> repo root
# Read the specialist prompt from the shipping file, never a staged copy. A copy is a drift
# site: the benchmark would keep measuring a stale version of the prompt it claims to test.
VERIFIER_PROMPT = REPO / "agents" / "verifier.md"
GEMINI_CALLER = HERE / "gemini-call.py"

# Exact model ids, pinned. Never a "-latest" alias: an alias silently changes what a
# published number was measured on.
TARGETS = [
    {"key": "claude-haiku", "transport": "claude", "model": "claude-haiku-4-5-20251001", "family": "Claude", "tier": "small"},
    {"key": "claude-sonnet", "transport": "claude", "model": "claude-sonnet-5", "family": "Claude", "tier": "mid"},
    {"key": "claude-opus", "transport": "claude", "model": "claude-opus-5", "family": "Claude", "tier": "frontier"},
    {"key": "gpt-5", "transport": "codex", "model": "gpt-5.6-luna", "family": "OpenAI", "tier": "mid"},
    {"key": "gpt-6", "transport": "codex", "model": "gpt-6-astra", "family": "OpenAI", "tier": "frontier"},
    {"key": "gemini-flash", "transport": "gemini", "model": "gemini-3.8-flash", "family": "Google", "tier": "mid"},
    {"key": "gemini-pro", "transport": "gemini", "model": "gemini-3.1-pro-preview", "family": "Google", "tier": "frontier"},
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
    ap.add_argument("--input", help="file holding the user message, sent verbatim to both arms")
    ap.add_argument("--outdir", default="out-crossmodel")
    ap.add_argument("--only", help="run a single target key")
    ap.add_argument("--probe", action="store_true", help="isolation probe only, no eval")
    ap.add_argument("--check", action="store_true",
                    help="report which targets this machine can run, then exit. Spends nothing.")
    ap.add_argument("--dry-run", action="store_true",
                    help="print every call that would be made, without making any of them")
    ap.add_argument("--force", action="store_true",
                    help="regenerate cells that already have an output file on disk")
    a = ap.parse_args()

    env = gemini_env()
    targets = [t for t in TARGETS if not a.only or t["key"] == a.only]

    avail = availability(env)
    print("Targets on this machine:")
    for t in TARGETS:
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
        if not a.input:
            sys.exit("ERROR: --dry-run still needs --input, so the plan reflects the real run")
        # Plan every REQUESTED target, not only the runnable ones. A new user with nothing
        # set up still needs to see the whole shape of the run before deciding to set it up.
        plan = [x for x in TARGETS if not a.only or x["key"] == a.only]
        n = len(plan) * 2 * len(REPS)
        print(f"\nDRY RUN. {n} calls would be made ({len(plan)} targets x 2 arms x k={len(REPS)}).")
        print(f"Input sent verbatim to both arms: {a.input}")
        print(f"Arm A: no system prompt. Arm B: {VERIFIER_PROMPT.name} as the system prompt.")
        for t in plan:
            sysnote = {
                "claude": "--system-prompt-file",
                "gemini": "systemInstruction field",
                "codex": "PREPENDED to the user message (codex exec has no system-prompt flag)",
            }[t["transport"]]
            print(f"\n  {t['key']}  ({t['family']}, {t['model'] or 'codex default'})")
            print(f"    transport   : {t['transport']}")
            print(f"    arm B via   : {sysnote}")
            print(f"    would write : {a.outdir}/{t['key']}-{{A,B}}{{1..{len(REPS)}}}.md")
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

    if not a.input:
        sys.exit("ERROR: --input is required")
    if not VERIFIER_PROMPT.exists():
        sys.exit(f"ERROR: specialist prompt not found at {VERIFIER_PROMPT}. "
                 "Arm B would run bare and the result would read as a null finding.")

    user_path = pathlib.Path(a.input)
    user_text = user_path.read_text(encoding="utf-8")
    outdir = HERE / a.outdir
    outdir.mkdir(exist_ok=True)

    manifest = []
    for t in targets:
        for arm in ("A", "B"):
            for rep in REPS:
                name = f"{t['key']}-{arm}{rep}.md"
                out_path = outdir / name

                # A cell already on disk is not re-run. A partial run that crashes
                # mid-sweep (the first attempt died on a cp1252 decode after 6 of 16
                # cells) should not cost the whole sweep's quota again. --force overrides.
                if out_path.exists() and out_path.stat().st_size > 0 and not a.force:
                    print(f"  skip {name}  (exists; --force to regenerate)")
                    manifest.append({**t, "arm": arm, "rep": rep, "file": name,
                                     "ok": True, "reused": True,
                                     "chars": len(out_path.read_text(encoding="utf-8"))})
                    continue

                sysp = VERIFIER_PROMPT if arm == "B" else None
                t0 = time.time()
                if t["transport"] == "claude":
                    txt, err = run_claude(t["model"], sysp, user_text, out_path)
                elif t["transport"] == "codex":
                    txt, err = run_codex(t["model"], sysp, user_text, out_path)
                else:
                    txt, err = run_gemini(t["model"], sysp, user_path, out_path, env)

                if err:
                    print(f"  FAIL {name}: {err}")
                    manifest.append({**t, "arm": arm, "rep": rep, "file": name,
                                     "ok": False, "error": err})
                    continue
                if txt and not out_path.exists():
                    out_path.write_text(txt + "\n", encoding="utf-8")
                print(f"  ok   {name}  ({len(txt)} chars, {time.time()-t0:.0f}s)")
                manifest.append({**t, "arm": arm, "rep": rep, "file": name,
                                 "ok": True, "chars": len(txt)})

    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    ok = sum(1 for m in manifest if m["ok"])
    print(f"\n{ok} of {len(manifest)} cells produced output. Failures are unmeasured, not clean.")


if __name__ == "__main__":
    main()
