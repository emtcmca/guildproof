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
        out2 = r2.stdout + r2.stderr
        check("an empty cells dir exits non-zero", r2.returncode != 0, f"exit {r2.returncode}")
        # An empty directory now fails on the missing manifest before it counts cells, which is
        # the more useful complaint: there is no run there, not merely no outputs yet.
        check("and says there is no run to score",
              "no run to score" in out2 or "holds no cells" in out2, out2[-200:])

        # A directory that HAS a manifest but no cells must still refuse, so the cell count
        # stays a real gate rather than something the manifest check happens to shadow.
        with_manifest = tmp / "declared-but-empty"
        with_manifest.mkdir()
        cc.write_manifest(with_manifest, {
            "schema": cc.SCHEMA, "run_id": "empty", "input": "i", "system_prompt": "s",
            "reps": 2, "judge_model": "j", "judges_per_target": 2,
            "checklist": ["one"],
            "targets": [{"key": "a", "transport": "claude", "model": "m"}],
            "labels": {"seed": "s"},
        })
        r3 = subprocess.run(
            [sys.executable, str(HERE / "judge-crossmodel.py"), "--tabulate",
             "--cells", str(with_manifest)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        out3 = r3.stdout + r3.stderr
        check("a declared run with zero cells exits non-zero", r3.returncode != 0,
              f"exit {r3.returncode}")
        check("and names the count it found", "holds no cells" in out3, out3[-200:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_no_duplicate_config():
    """The judge must not grow its own roster, permutation table or checklist again.

    Those three lists were duplicates of things the runner also knew, maintained by hand in two
    files. An outside user has to edit the roster, because nobody else has the author's twelve
    models — and editing the runner alone left the judge scoring the old list in silence.
    """
    print("\nTHE JUDGE CARRIES NO RUN CONFIGURATION")
    judge = (HERE / "judge-crossmodel.py").read_text(encoding="utf-8")
    checks = {
        "no roster literal": 'TARGETS = ["claude' not in judge and "TARGETS = ['claude" not in judge,
        "no permutation table literal": '{"W": ' not in judge,
        "no inline checklist": '"Gives a tri-state verdict' not in judge,
        "reads the manifest": "cc.read_manifest(" in judge,
        "takes permutations from the manifest": "cc.permutations_for(" in judge,
    }
    for name, ok in checks.items():
        check(name, ok)
    runner = (HERE / "run-crossmodel.py").read_text(encoding="utf-8")
    check("the runner's roster is marked as a default, not the run",
          "SHIPPED_TARGETS" in runner and "TARGETS = [" not in runner.replace("SHIPPED_TARGETS = [", ""))
    check("the runner writes the manifest", "cc.write_manifest(" in runner)

    # Neither script may assume exactly two arms. A hardcoded 2 here does not crash and does not
    # change what runs; it silently MISREPORTS a three-arm run as a two-arm one, which is how a
    # dry-run came back saying "12 calls, 2 arms" for an 18-call run. Cheap to check, invisible
    # otherwise.
    for label, src in (("runner", runner), ("judge", judge)):
        hard = [ln.strip() for ln in src.splitlines()
                if ("* 2 *" in ln or "2 arms" in ln or "both arms" in ln
                    or '("A", "B")' in ln)
                and not ln.strip().startswith("#")]
        check(f"{label} does not hardcode two arms", not hard, f"found: {hard[:3]}")


def t_sidecars_are_not_artifacts():
    """A fingerprint sidecar must never be mistaken for the artifact it describes.

    `score-X-1.json.fingerprint.json` matches the glob `score-*.json`, so the sidecars were
    counted as scorecards: a 6-scorecard run reported "12 scorecards, 6 provably scored" and then
    listed the six sidecars as unfingerprinted evidence. No tally was wrong, because a sidecar has
    no "outputs" key, but the provenance line is the part a reader checks.
    """
    print("\nSIDECARS ARE NOT ARTIFACTS")
    judge = (HERE / "judge-crossmodel.py").read_text(encoding="utf-8")
    check("the scorecard scan excludes sidecars", '.fingerprint.json"' in judge)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gp-selftest-"))
    try:
        real = tmp / "score-alpha-1.json"
        real.write_text('{"outputs": []}', encoding="utf-8")
        cc.write_sidecar(real, "deadbeef", note="selftest")
        both = sorted(p.name for p in tmp.glob("score-*.json"))
        check("the naive glob does catch both (this is why the filter exists)", len(both) == 2,
              str(both))
        filtered = [p for p in tmp.glob("score-*.json")
                    if not p.name.endswith(".fingerprint.json")]
        check("the filter leaves exactly the real scorecard",
              [p.name for p in filtered] == ["score-alpha-1.json"], str(filtered))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_derived_permutation():
    """A permutation derived from the roster cannot fall out of sync with the roster."""
    print("\nDERIVED BLINDING")
    a = cc.derive_permutation("seed-1", "claude-opus")
    check("same seed and target is stable", a == cc.derive_permutation("seed-1", "claude-opus"))
    check("a different seed moves it", a != cc.derive_permutation("seed-2", "claude-opus"))
    check("a different target moves it", a != cc.derive_permutation("seed-1", "gemini-pro"))
    check("all four labels are used", sorted(a) == sorted(cc.LABEL_POOL[:4]))
    cells = sorted(tuple(v) for v in a.values())
    check("every arm/rep cell appears exactly once",
          cells == [("A", 1), ("A", 2), ("B", 1), ("B", 2)], str(cells))
    # Across a roster, label position must not track the arm, or the blinding is decorative.
    roster = [f"t{i}" for i in range(12)]
    w_arms = {t: cc.derive_permutation("s", t)["W"][0] for t in roster}
    check("label W is not the same arm for every target",
          len(set(w_arms.values())) > 1, str(w_arms))


def t_manifest_drives_the_judge():
    """A 2-target run, fabricated on disk, must blind exactly as its own manifest says.

    Nothing here calls a model: the cells are placeholder text. What is under test is that the
    judge takes its roster, reps, labels and checklist from the manifest rather than from
    anything baked into the script.
    """
    print("\nA MANIFEST DEFINES THE RUN END TO END")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gp-selftest-"))
    try:
        manifest = {
            "schema": cc.SCHEMA, "run_id": "selftest-2-target",
            "input": "evals/benchmarks/fixtures/v2-invoice-subtle.md",
            "system_prompt": "agents/verifier.md",
            "reps": 2, "judge_model": "claude-sonnet-5", "judges_per_target": 2,
            "checklist_source": "selftest", "checklist": cc.DEFAULT_CHECKLIST[:2],
            "targets": [
                {"key": "alpha", "transport": "claude", "model": "m-1",
                 "family": "F", "tier": "t"},
                {"key": "beta", "transport": "gemini", "model": "m-2",
                 "family": "G", "tier": "t"},
            ],
            "labels": {"seed": "selftest-seed"},
        }
        cc.write_manifest(tmp, manifest)
        for t in ("alpha", "beta"):
            for arm in ("A", "B"):
                for rep in (1, 2):
                    (tmp / f"{t}-{arm}{rep}.md").write_text(
                        f"placeholder cell {t} {arm}{rep}\n", encoding="utf-8")

        r = subprocess.run(
            [sys.executable, str(HERE / "judge-crossmodel.py"), "--blind", "--cells", str(tmp)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        out = r.stdout + r.stderr
        check("blinding a manifest-defined run succeeds", r.returncode == 0, out[-300:])
        check("it reports the manifest's roster size, not the shipped one",
              "2 targets" in out, out[:200])
        check("it reports the manifest's checklist length",
              "2 checklist items" in out, out[:200])
        bundles = sorted(p.name for p in (tmp / "judge-bundles").glob("judge-in-*.md"))
        check("one bundle per manifest target",
              bundles == ["judge-in-alpha.md", "judge-in-beta.md"], str(bundles))

        key = (tmp / "label-key.csv").read_text(encoding="utf-8").splitlines()
        check("the label key has one row per cell", len(key) - 1 == 8, str(len(key) - 1))
        # The key must match what the seed derives, or the scores would be joined to the
        # wrong arm — a silent, total corruption of the result.
        derived = {(t, lab): tuple(v)
                   for t, m in cc.permutations_for(manifest).items() for lab, v in m.items()}
        on_disk = {(t, lab): (arm, int(rep))
                   for t, lab, arm, rep in (l.split(",") for l in key[1:])}
        check("the written key matches the derived permutation", derived == on_disk)
        # The label key must never travel inside a bundle.
        blob = "".join((tmp / "judge-bundles" / b).read_text(encoding="utf-8") for b in bundles)
        check("no bundle leaks an arm label",
              "arm" not in blob.lower() and "-A1" not in blob and "-B1" not in blob)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_manifest_validation():
    print("\nAN INCOMPLETE MANIFEST IS REFUSED")
    base = {
        "schema": cc.SCHEMA, "run_id": "r", "input": "i", "system_prompt": "s",
        "reps": 2, "judge_model": "j", "judges_per_target": 2,
        "checklist": ["one"],
        "targets": [{"key": "a", "transport": "claude", "model": "m"}],
        "labels": {"seed": "s"},
    }
    cc.validate_manifest(dict(base), "baseline")
    check("a complete manifest validates", True)
    for name, bad in (
        ("a missing key", {k: v for k, v in base.items() if k != "judge_model"}),
        ("a wrong schema", dict(base, schema="something-else/9")),
        ("an empty roster", dict(base, targets=[])),
        ("a target with no model", dict(base, targets=[{"key": "a", "transport": "claude"}])),
        ("a duplicate target key", dict(base, targets=[
            {"key": "a", "transport": "claude", "model": "m"},
            {"key": "a", "transport": "gemini", "model": "n"}])),
        ("an empty checklist", dict(base, checklist=[])),
        ("no seed and no permutations", dict(base, labels={})),
    ):
        try:
            cc.validate_manifest(bad, "bad")
            check(f"{name} is refused", False, "it was accepted")
        except ValueError:
            check(f"{name} is refused", True)


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
    t_no_duplicate_config()
    t_resolution()
    t_manifest_validation()
    t_sidecars_are_not_artifacts()
    t_derived_permutation()
    t_manifest_drives_the_judge()
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
