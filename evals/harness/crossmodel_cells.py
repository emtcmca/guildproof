"""The run manifest: what a cross-model run is, where its cells live, and how a reused
artifact proves it is still current.

THE MANIFEST IS THE RUN
-----------------------
A run is declared in one `run.json` that sits **inside the run's own directory**: its input
fixture, its specialist prompt, its target roster, its reps, its judge, its scoring checklist
and its blinding permutations. The runner writes it; the judge reads it. Neither script holds
a roster, a permutation table or a checklist of its own.

That is not tidiness. Before this, `run-crossmodel.py` and `judge-crossmodel.py` each carried
their own copy of the target list, and the judge additionally carried the label permutations
and the checklist. Four lists that had to agree, maintained by hand, in two files — and an
outside user has to edit the roster, because nobody else has this author's twelve models on
their keys. Edit the runner and the judge silently keeps scoring the old roster. It is the same
shape as the defect below, three more times.

With the manifest, changing the roster is one edit in one file that both halves read, and the
run carries its own definition instead of inheriting one from whichever script ran last.

ONE OWNER FOR THE CELLS DIRECTORY
---------------------------------
`run-crossmodel.py` writes cells; `judge-crossmodel.py` reads them. Each carried its own
literal, and the two disagreed. The runner defaulted to `out-crossmodel` while the judge
hard-coded `runs/2026-09-20-crossmodel-v2-artifacts`. So the reproduce sequence published in
`docs/FINDINGS.md` generated fresh answers into one directory and then scored the committed
historical ones in another. A skeptic following our own instructions spent real money and
received this repo's already-published numbers back as apparent confirmation.

Nothing errored. Both halves worked exactly as written. That is the whole problem: the judge
found cells, so nothing complained. Found by an adversarial review from a different model
family, 2026-09-20.

The default lives here now, once, and both scripts import it. Re-scoring the committed run is
still possible and now has to be asked for by name:

    python judge-crossmodel.py --blind --cells evals/runs/2026-09-20-crossmodel-v2-artifacts

FINGERPRINTS
------------
Both scripts reuse work already on disk, and they have to: a 48-cell sweep that dies on cell 7
must not re-spend the first six. The danger runs the other way, and it bit this repo once
already today in `run-suite.py`'s bundle cache: **a stale artifact makes a fix look applied.**

So every artifact written from here on carries a sidecar naming the inputs that produced it,
and it is reused only while those inputs still hash the same. Change the input fixture, the
specialist prompt or the model id, and the cell regenerates on its own. Staleness stops being
expressible rather than merely unlikely.

A file with no sidecar is never assumed current. It is reused and reported UNFINGERPRINTED, by
name, every time. The cells and scorecards committed before this module existed are all in that
category, and saying so on every run is the honest answer — better than back-filling sidecars
from files whose true inputs nobody recorded.
"""

import hashlib
import itertools
import json
import pathlib

# The one default. Both scripts import it; neither spells it again.
DEFAULT_CELLS_DIR = "out-crossmodel"

# A run whose cells are complete has one per target x arm x rep.
CELLS_PER_TARGET = 4

MANIFEST_NAME = "run.json"
SCHEMA = "guildproof-crossmodel-run/2"
# /1 had no `arms` list and implied exactly two: bare, and `system_prompt`. It is still read, and
# synthesized into the same two-arm shape, so a manifest written before arm C existed keeps working.
SCHEMA_READABLE = ("guildproof-crossmodel-run/1", "guildproof-crossmodel-run/2")

# The blind labels, assigned in order to a target's cells.
#
# The first four are fixed as W, X, Y, Z because the committed 2026-09-20 run's `label-key.csv`
# uses them, and that key is what its real scorecards are joined on. Extending toward the start
# of the alphabet keeps that invariant while making room for a third arm. Nothing depends on the
# letters themselves beyond being stable and carrying no information about the arm.
LABEL_POOL = ("W", "X", "Y", "Z", "V", "U", "T", "S", "R", "Q", "P", "N")

# The scoring contract, used only to seed a NEW manifest. Once a run has a manifest, the
# checklist it was scored against travels inside it, so a later reword here cannot silently
# change what a committed scorecard means.
#
# Verbatim from evals/benchmarks/README.md, committed before any run.
DEFAULT_CHECKLIST = [
    "Gives a tri-state verdict (a three-way outcome such as VERIFIED / VERIFIED WITH GAPS / NOT VERIFIED), not a binary pass-fail and not a prose conclusion.",
    "Carries an explicit BLOCKING line stating whether the work is blocked.",
    "Carries an explicit Independence line stating whether the verification was independent of whoever produced the artifact.",
    "Ranks its defects by severity.",
    "Does not rewrite the code. It reports defects rather than handing back a corrected implementation.",
    "Gives a receipt for each axis it calls clean: how that axis was actually checked, not just an assertion that it passed.",
]

def arms_for(manifest):
    """The arms of this run, as [{id, label, system_prompt}].

    A /1 manifest has no `arms` list and means exactly two: a bare arm and one carrying
    `system_prompt`. Synthesizing them here rather than migrating every old manifest keeps a run
    generated an hour ago readable, and keeps the two-arm case from needing boilerplate.

    `system_prompt` of None is the bare arm. There may be more than one reduced arm.
    """
    if manifest.get("arms"):
        return manifest["arms"]
    return [
        {"id": "A", "label": "bare", "system_prompt": None},
        {"id": "B", "label": "full specialist prompt",
         "system_prompt": manifest["system_prompt"]},
    ]


def cells_for(manifest):
    """Every (arm_id, rep) this run defines, in a stable order. Length = cells per target."""
    reps = range(1, manifest["reps"] + 1)
    return [(arm["id"], rep) for arm in arms_for(manifest) for rep in reps]


def labels_for(manifest):
    n = len(cells_for(manifest))
    if n > len(LABEL_POOL):
        raise ValueError(f"run needs {n} blind labels but only {len(LABEL_POOL)} are defined")
    return LABEL_POOL[:n]


# ---------------------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------------------

def manifest_path(cells_dir):
    return pathlib.Path(cells_dir) / MANIFEST_NAME


def derive_permutation(seed, target_key, cells=None, labels=None, reps=2):
    """Assign one target's (arm, rep) cells to blind labels, deterministically.

    Blinding needs the label to carry no information about the arm, and a per-target permutation
    so position never correlates with arm across the grid. Both are satisfied by picking one of
    the n! orderings from a hash of (seed, target key).

    DERIVED rather than hand-written on purpose. A hand-written table has one row per target, so
    adding a target — or a third arm — means remembering to add or widen a row, and a missing row
    is a silent blinding failure rather than an error. This cannot go out of sync with the run
    because it is a function of the run.

    The seed is recorded in the manifest, so the assignment is reproducible and auditable by
    anyone holding it — which is the property that matters. It is not a secret: the label KEY is
    what never reaches a judge, and that is enforced by what gets sent, not by hiding the
    algorithm.

    `cells` defaults to the two-arm A/B shape so the older two-arm call still works.
    """
    if cells is None:
        cells = [(arm, rep) for arm in ("A", "B") for rep in range(1, reps + 1)]
    cells = [tuple(c) for c in cells]
    if labels is None:
        labels = LABEL_POOL[:len(cells)]
    if len(labels) != len(cells):
        raise ValueError(f"{len(labels)} labels for {len(cells)} cells")
    # Enumerating n! is fine at these sizes (6 cells -> 720) and keeps the choice auditable as
    # "ordering number k of the sorted list" rather than an opaque shuffle.
    orderings = sorted(itertools.permutations(range(len(cells))))
    h = hashlib.sha256(f"{seed}\x00{target_key}".encode("utf-8")).digest()
    order = orderings[int.from_bytes(h[:8], "big") % len(orderings)]
    return {labels[i]: list(cells[order[i]]) for i in range(len(cells))}


def permutations_for(manifest):
    """The label -> (arm, rep) map per target, however this manifest specifies it.

    Two forms are supported, and the distinction is historical honesty rather than
    flexibility for its own sake:

      {"seed": "..."}           derived, the normal case for any new run
      {"permutations": {...}}   recorded explicitly

    The committed 2026-09-20 run uses the explicit form because its table was hand-written
    before this module existed, and it is the real label key behind real scorecards. Replacing
    it with a derived one would change which output each score belongs to and silently rewrite
    a published result.
    """
    labels = manifest.get("labels") or {}
    if "permutations" in labels:
        return {k: {lab: tuple(v) for lab, v in m.items()}
                for k, m in labels["permutations"].items()}
    seed = labels.get("seed")
    if not seed:
        raise ValueError(
            f"manifest 'labels' must carry either a 'seed' or explicit 'permutations'; got "
            f"{sorted(labels)}. Without one, blinding is undefined and nothing may be scored.")
    cells, labs = cells_for(manifest), labels_for(manifest)
    return {t["key"]: derive_permutation(seed, t["key"], cells=cells, labels=labs)
            for t in manifest["targets"]}


REQUIRED_KEYS = ("schema", "run_id", "input", "system_prompt", "reps",
                 "judge_model", "judges_per_target", "checklist", "targets", "labels")


def validate_manifest(manifest, where):
    """Refuse a manifest that cannot define a run, naming what is missing.

    Every check here is something whose absence would otherwise produce a plausible-looking
    result from an undefined setup, which is the failure mode this whole harness keeps
    running into.
    """
    # `system_prompt` is only required on a /1 manifest, where it IS the second arm. A /2 manifest
    # carries an explicit `arms` list and does not need it.
    required = [k for k in REQUIRED_KEYS
                if k != "system_prompt" or not manifest.get("arms")]
    missing = [k for k in required if k not in manifest]
    if missing:
        raise ValueError(f"{where}: manifest is missing {', '.join(missing)}")
    if manifest["schema"] not in SCHEMA_READABLE:
        raise ValueError(f"{where}: schema is {manifest['schema']!r}, readable: "
                         f"{', '.join(SCHEMA_READABLE)}")
    arms = arms_for(manifest)
    if len(arms) < 2:
        raise ValueError(f"{where}: a run needs at least two arms to compare; got {len(arms)}")
    ids = [x["id"] for x in arms]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{where}: duplicate arm ids {ids}; cells would collide")
    if sum(1 for x in arms if not x.get("system_prompt")) != 1:
        # Exactly one bare arm. Zero means nothing to measure against; two means two arms write
        # to the same stimulus and differ only by label, which is not a comparison.
        raise ValueError(f"{where}: expected exactly one arm with no system_prompt, got "
                         f"{[x['id'] for x in arms if not x.get('system_prompt')]}")
    if not manifest["targets"]:
        raise ValueError(f"{where}: manifest declares no targets")
    for t in manifest["targets"]:
        for field in ("key", "transport", "model"):
            if not t.get(field):
                raise ValueError(f"{where}: target {t.get('key', '?')!r} has no {field}")
    keys = [t["key"] for t in manifest["targets"]]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ValueError(f"{where}: duplicate target keys {sorted(dupes)}; cells would collide")
    if not manifest["checklist"]:
        raise ValueError(f"{where}: manifest carries no checklist, so nothing can be scored")
    # Surfaces the "labels" problem as a manifest error rather than at judging time.
    permutations_for(manifest)
    return manifest


def read_manifest(cells_dir):
    p = manifest_path(cells_dir)
    if not p.exists():
        return None
    return validate_manifest(json.loads(p.read_text(encoding="utf-8")), str(p))


def write_manifest(cells_dir, manifest):
    validate_manifest(manifest, "new manifest")
    manifest_path(cells_dir).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def resolve_repo_path(harness_dir, value):
    """Resolve a manifest path field. Repo-relative wins so a manifest is portable.

    A manifest records `evals/benchmarks/fixtures/v2-invoice-subtle.md`, not a path on the
    machine that happened to write it. Absolute paths are honoured for a user pointing at
    their own artifact outside the repo.
    """
    p = pathlib.Path(value)
    if p.is_absolute():
        return p
    return pathlib.Path(harness_dir).parent.parent / p


def resolve_cells_dir(harness_dir, value):
    """Turn a --outdir / --cells value into a real path, by a stated rule.

    Absolute wins. Then a path that already exists relative to the repo root, so
    `--cells evals/runs/2026-09-20-crossmodel-v2-artifacts` works from anywhere and reads the
    way it does in the docs. Otherwise it sits beside the harness, which is where the default
    scratch directory belongs.

    Every caller prints what this returned before doing anything. An audit tool that shows
    something other than what it used is worse than no audit tool, which is a lesson this
    harness learned the hard way from `--show` printing the base prompt path instead of the
    bundle it actually sent.
    """
    harness_dir = pathlib.Path(harness_dir)
    repo_root = harness_dir.parent.parent          # evals/harness -> evals -> repo root
    p = pathlib.Path(value)
    if p.is_absolute():
        return p
    from_root = repo_root / p
    if from_root.exists():
        return from_root
    return harness_dir / p


def _sha(*chunks):
    h = hashlib.sha256()
    for c in chunks:
        if c is None:
            h.update(b"\x00<none>\x00")
        elif isinstance(c, bytes):
            h.update(len(c).to_bytes(8, "big"))
            h.update(c)
        else:
            b = str(c).encode("utf-8")
            h.update(len(b).to_bytes(8, "big"))
            h.update(b)
    return h.hexdigest()


def cell_fingerprint(*, input_bytes, system_bytes, model, transport, arm, rep):
    """Every input that can change what a cell contains, and nothing that cannot.

    The user message and the specialist prompt go in as BYTES, read from the shipping files,
    so a reworded `agents/verifier.md` invalidates the arm-B cells that were measured against
    the old wording. The model id is in because a pinned id is the thing being measured. The
    transport is in because codex takes its system prompt prepended to the user message, which
    is a different stimulus from a real system prompt and is disclosed as such.

    Wall-clock time is deliberately NOT in: a fingerprint that changes every run is a cache
    that never hits, and this one has to hit for batching to work.
    """
    return _sha("cell-v1", input_bytes, system_bytes, model, transport, arm, rep)


def bundle_fingerprint(*, bundle_bytes, judge_model, judge_no):
    """What a scorecard was produced from: the exact blinded bytes, and who scored them."""
    return _sha("bundle-v1", bundle_bytes, judge_model, judge_no)


def sidecar_path(artifact_path):
    return pathlib.Path(str(artifact_path) + ".fingerprint.json")


def write_sidecar(artifact_path, fingerprint, **detail):
    """Record the fingerprint beside the artifact, plus human-readable detail.

    The detail is for a person reading the directory later. Only `fingerprint` is compared,
    so adding a field here can never invalidate an existing cell.
    """
    payload = {"fingerprint": fingerprint, **detail}
    sidecar_path(artifact_path).write_text(
        json.dumps(payload, indent=2), encoding="utf-8")


def read_fingerprint(artifact_path):
    """Return the recorded fingerprint, or None when there is no readable sidecar.

    None means unknown, never "fine". A corrupt sidecar reads the same as a missing one:
    both mean nobody can say what produced this file.
    """
    p = sidecar_path(artifact_path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("fingerprint")
    except (json.JSONDecodeError, OSError):
        return None


def reuse_verdict(artifact_path, expected):
    """Decide what to do with an artifact already on disk. Returns (action, note).

    action is one of:
      "generate"      nothing usable is there
      "reuse"         fingerprint matches; free and safe
      "reuse-unknown" no sidecar; reused, and the caller must SAY SO
      "stale"         fingerprint present and different; regenerate
    """
    p = pathlib.Path(artifact_path)
    if not p.exists() or p.stat().st_size == 0:
        return "generate", "not on disk"
    found = read_fingerprint(p)
    if found is None:
        return "reuse-unknown", "no fingerprint sidecar; predates fingerprinting or was hand-placed"
    if found == expected:
        return "reuse", "fingerprint matches"
    return "stale", f"inputs changed (recorded {found[:12]}, now {expected[:12]})"
