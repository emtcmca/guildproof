"""Where the cross-model cells live, and how a reused artifact proves it is still current.

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
import json
import pathlib

# The one default. Both scripts import it; neither spells it again.
DEFAULT_CELLS_DIR = "out-crossmodel"

# A run whose cells are complete has one per target x arm x rep.
CELLS_PER_TARGET = 4


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
