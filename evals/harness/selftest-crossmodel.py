"""Prove the reproduce-path fix, without spending a token.

Two defects are under test, both found by the first Codex adversarial review on 2026-09-20:

  1. The runner and the judge disagreed about which directory held the cells, so the published
     reproduce sequence generated fresh answers and then scored the committed historical ones.
  2. Nothing on disk recorded what produced it, so a cell or a scorecard could be reused after
     its inputs had changed. That same class of bug made a fix look applied earlier the same
     day in `run-suite.py`'s bundle cache.

Neither defect raised an error when it was live. Both halves worked exactly as written. So the
only thing that can hold the fix in place is a check that fails when it regresses.

    python evals/harness/selftest-crossmodel.py     exit 0 = all assertions hold

Every case here runs on temporary files and makes no model call.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")  # cp1252 consoles otherwise kill this on a dash

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import crossmodel_cells as cc  # noqa: E402

FAILS = []


def check(name, condition, detail=""):
    print(f"  {'ok  ' if condition else 'FAIL'}  {name}")
    if not condition:
        if detail:
            print(f"          {detail}")
        FAILS.append(name)


def t_one_owner():
    """The two scripts must not carry separate literals for the cells directory again.

    This is the defect itself, so it is checked against the source text: any future edit that
    re-introduces a hard-coded artifacts path in either script trips this.
    """
    print("\nONE OWNER FOR THE CELLS DIRECTORY")
    runner = (HERE / "run-crossmodel.py").read_text(encoding="utf-8")
    judge = (HERE / "judge-crossmodel.py").read_text(encoding="utf-8")
    for label, src in (("runner", runner), ("judge", judge)):
        check(f"{label} imports the shared module", "import crossmodel_cells" in src)
        # The committed run may be NAMED in prose and in --help, where it is documentation.
        # What must not come back is that name assembled into a path: a ` / ` join or a
        # Path(...) call. That is the exact shape of the original defect.
        bad = [ln.strip() for ln in src.splitlines()
               if "crossmodel-v2-artifacts" in ln
               and (" / " in ln or "Path(" in ln)
               and not ln.strip().startswith("#")]
        check(f"{label} does not build a path to the committed run", not bad,
              f"found: {bad[:2]}")
    check("both defaults are the same object",
          f'default=cc.DEFAULT_CELLS_DIR' in runner and 'default=cc.DEFAULT_CELLS_DIR' in judge)


def t_resolution():
    print("\nPATH RESOLUTION")
    harness = HERE
    repo = harness.parent.parent
    # A path that exists relative to the repo root wins, so --cells reads the way the docs
    # write it rather than needing ../runs/.
    committed = "evals/runs/2026-09-20-crossmodel-v2-artifacts"
    if (repo / committed).exists():
        check("a repo-relative path resolves against the repo root",
              cc.resolve_cells_dir(harness, committed) == repo / committed)
    check("the default sits beside the harness",
          cc.resolve_cells_dir(harness, cc.DEFAULT_CELLS_DIR) == harness / cc.DEFAULT_CELLS_DIR)
    # Not .resolve()d: on macOS /tmp is a symlink to /private/tmp, and resolve_cells_dir
    # deliberately hands an absolute path back untouched rather than normalising it.
    abs_path = pathlib.Path(tempfile.gettempdir())
    check("an absolute path is taken as given",
          cc.resolve_cells_dir(harness, str(abs_path)) == abs_path)


def t_fingerprints():
    print("\nFINGERPRINTS DISTINGUISH WHAT THEY MUST")
    base = dict(input_bytes=b"artifact text", system_bytes=b"verifier prompt",
                model="claude-opus-5", transport="claude", arm="B", rep=1)
    ref = cc.cell_fingerprint(**base)
    check("identical inputs hash identically", cc.cell_fingerprint(**base) == ref)
    for field, changed in (
        ("the user message", dict(base, input_bytes=b"artifact texT")),
        ("the specialist prompt", dict(base, system_bytes=b"verifier prompt.")),
        ("the model id", dict(base, model="claude-sonnet-5")),
        ("the transport", dict(base, transport="codex")),
        ("the arm", dict(base, system_bytes=None, arm="A")),
        ("the rep", dict(base, rep=2)),
    ):
        check(f"a change to {field} changes the fingerprint",
              cc.cell_fingerprint(**changed) != ref)
    # Concatenation must not be able to collide: ("ab", "c") and ("a", "bc") are different
    # inputs and a naive hash of the joined bytes would call them the same cell.
    check("field boundaries cannot be smuggled across",
          cc.cell_fingerprint(**dict(base, input_bytes=b"ab", system_bytes=b"c"))
          != cc.cell_fingerprint(**dict(base, input_bytes=b"a", system_bytes=b"bc")))


def t_reuse_verdicts():
    print("\nREUSE VERDICTS")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gp-selftest-"))
    try:
        cell = tmp / "claude-opus-B1.md"
        fp = cc.cell_fingerprint(input_bytes=b"in", system_bytes=b"sys",
                                 model="m", transport="claude", arm="B", rep=1)

        check("a missing file generates", cc.reuse_verdict(cell, fp)[0] == "generate")

        cell.write_text("", encoding="utf-8")
        check("an empty file generates", cc.reuse_verdict(cell, fp)[0] == "generate")

        cell.write_text("a verdict\n", encoding="utf-8")
        check("a file with no sidecar is reused but flagged unknown",
              cc.reuse_verdict(cell, fp)[0] == "reuse-unknown")

        cc.write_sidecar(cell, fp, note="written by the selftest")
        check("a matching fingerprint reuses", cc.reuse_verdict(cell, fp)[0] == "reuse")

        other = cc.cell_fingerprint(input_bytes=b"in2", system_bytes=b"sys",
                                    model="m", transport="claude", arm="B", rep=1)
        check("changed inputs read as stale, not as reusable",
              cc.reuse_verdict(cell, other)[0] == "stale")

        cc.sidecar_path(cell).write_text("{ not json", encoding="utf-8")
        check("a corrupt sidecar is unknown, never trusted",
              cc.reuse_verdict(cell, fp)[0] == "reuse-unknown")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_judge_refuses_empty():
    """The judge must refuse a cells directory it cannot score, rather than find another one.

    This is the exact failure: the old judge always had somewhere valid to go, so the
    mismatch never surfaced. A hard refusal is what makes it surface.

    Both probes use --tabulate, which never writes, and that is not a stylistic choice. The
    first version of this test used --blind. Under the mutation that restores the hard-coded
    path, --blind resolved to the COMMITTED artifacts directory and rewrote thirteen evidence
    files. They came back byte-identical apart from line endings, so nothing was lost, but a
    test that can overwrite the run it is defending is its own defect. A read-only probe is
    safe no matter what the code under test does with the path.
    """
    print("\nTHE JUDGE REFUSES RATHER THAN WANDERING")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gp-selftest-"))
    try:
        missing = tmp / "does-not-exist"
        r = subprocess.run(
            [sys.executable, str(HERE / "judge-crossmodel.py"), "--tabulate",
             "--cells", str(missing)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        check("a missing cells dir exits non-zero", r.returncode != 0, f"exit {r.returncode}")
        check("and says how to fix it",
              "run-crossmodel.py" in (r.stdout + r.stderr))

        r2 = subprocess.run(
            [sys.executable, str(HERE / "judge-crossmodel.py"), "--tabulate", "--cells", str(tmp)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        check("an empty cells dir exits non-zero", r2.returncode != 0, f"exit {r2.returncode}")
        check("and names the count it found",
              "holds no cells" in (r2.stdout + r2.stderr))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_force_writes():
    """--force must overwrite the cell it just paid for.

    The old line was `if txt and not out_path.exists()`, which made --force worse than a
    no-op: it spent the call, received the new answer, and kept the old file. Checked against
    the source because reproducing it needs a real model call.
    """
    print("\n--force OVERWRITES")
    src = (HERE / "run-crossmodel.py").read_text(encoding="utf-8")
    check("the write is not gated on the file being absent",
          "if txt and not out_path.exists():" not in src)
    check("a fresh cell writes and records a sidecar",
          "cc.write_sidecar(" in src)


if __name__ == "__main__":
    print("SELFTEST: the cross-model reproduce path")
    t_one_owner()
    t_resolution()
    t_fingerprints()
    t_reuse_verdicts()
    t_judge_refuses_empty()
    t_force_writes()
    print(f"\n{len(FAILS)} failure(s)")
    if FAILS:
        for f in FAILS:
            print(f"  - {f}")
        sys.exit(1)
    print("All assertions hold. No model call was made.")
