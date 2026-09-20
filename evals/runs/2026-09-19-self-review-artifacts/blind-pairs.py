"""Strip arm-revealing lines from each review and write blind A/B pairs for the judge.

The mapping below is fixed before the judge runs and kept out of the judge's inputs.
"""
import re, pathlib

S = pathlib.Path(__file__).parent
REVEAL = re.compile(
    r"independen|\bI wrote\b|\bI authored\b|earlier in (this|the same) conversation|"
    r"\bmy own\b|same session|builder's reasoning|fresh conversation|first encounter",
    re.I,
)
# Label assignment, chosen by hand to alternate; the judge never sees this file.
MAPPING = {
    ("t1", "frontier"): {"A": "fresh", "B": "self"},
    ("t1", "haiku"):    {"A": "self",  "B": "fresh"},
    ("t2", "frontier"): {"A": "self",  "B": "fresh"},
    ("t2", "haiku"):    {"A": "fresh", "B": "self"},
    ("t3", "frontier"): {"A": "fresh", "B": "self"},
    ("t3", "haiku"):    {"A": "self",  "B": "fresh"},
}

def redact(text):
    out, skip_next = [], False
    for line in text.splitlines():
        if skip_next and line.strip():
            skip_next = False
            continue
        if re.match(r"^#+\s*independence", line, re.I):
            skip_next = True
            continue
        if REVEAL.search(line):
            continue
        out.append(line)
    return "\n".join(out)

for (task, model), labels in MAPPING.items():
    parts = []
    for label in ("A", "B"):
        arm = labels[label]
        body = redact((S / f"rv-{arm}-{task}-{model}.md").read_text(encoding="utf-8"))
        parts.append(f"=== REVIEW {label} ===\n{body}\n")
    (S / f"judge-in-{task}-{model}.md").write_text("\n".join(parts), encoding="utf-8")
    left = sum(bool(REVEAL.search(p)) for p in parts)
    print(task, model, "written; revealing lines left:", left)
