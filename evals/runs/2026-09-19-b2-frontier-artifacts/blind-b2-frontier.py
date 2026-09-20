"""Strip meta self-description from each B2 output and write blind four-way bundles for the judge.

Two rules this script exists to enforce:

1. Redaction is NARROW. In B2 the scored behaviors ARE output structure (a verifier's
   "Independence" line is a scored behavior), so nothing structural may be stripped. Only
   *meta* self-description goes: sentences about the responder's instructions, role
   assignment, the tool's name, or the staged file paths. Stripping a scored heading would
   hand arm B a loss it did not earn.
2. The label key is computed here and never written into a judge input file.

Run: python blind-b2.py
"""
import re
import pathlib

S = pathlib.Path(__file__).parent
OUT = S / "out-frontier"
JUDGE = S / "judge-frontier"
JUDGE.mkdir(exist_ok=True)

SPECIALISTS = ["debugger", "security-review", "api-reviewer", "verifier"]

# Meta self-description only. Each pattern matches a line whose job is to describe the
# responder's own instructions rather than to answer the question.
META = re.compile(
    r"guildproof|promptsmith|"
    r"my (system )?prompt|per my instructions|as instructed|"
    r"the (prompt|instruction) file|prompt-(debugger|security-review|api-reviewer|verifier)|"
    r"\bAppData\b|scratchpad|"
    r"(acting|operating|responding) as (the|a) [a-z-]+ (agent|role|specialist)|"
    r"in my role as|I have been (given|assigned|instructed)|"
    r"my (assigned )?role (is|as)|following the method (in|from)",
    re.I,
)

# Fixed label assignment, alternated by hand so arm B is not always the same letter.
# The judge never receives this table.
MAPPING = {
    "debugger":        {"W": ("B", 2), "X": ("A", 2), "Y": ("B", 1), "Z": ("A", 1)},
    "security-review": {"W": ("A", 1), "X": ("B", 1), "Y": ("A", 2), "Z": ("B", 2)},
    "api-reviewer":    {"W": ("A", 2), "X": ("B", 2), "Y": ("B", 1), "Z": ("A", 1)},
    "verifier":        {"W": ("B", 1), "X": ("A", 1), "Y": ("A", 2), "Z": ("B", 2)},
}


# Clause-level redactions, applied INSIDE a line that must otherwise survive.
# This exists because of a real case: verifier-B2's "Independence:" line is itself a scored
# behavior, and it also contained a sentence naming the system prompt. Dropping the line would
# have cost arm B a point it earned; leaving it would have told the judge which arm wrote it.
# Each entry replaces the revealing clause with a visible marker, so the redaction is auditable.
CLAUSE = [
    re.compile(
        r"\s*(This artifact was not written in this conversation, but the system prompt that framed"
        r" it was\.|but the system prompt that framed it was\.)",
        re.I,
    ),
    re.compile(r"\s*I did not write the code, but I note the framing\.", re.I),
]


def redact(text):
    """Drop meta self-description lines; redact revealing clauses inside lines that must stay."""
    kept, dropped, clauses = [], [], []
    for line in text.splitlines():
        if META.search(line):
            dropped.append(line.strip())
            continue
        new = line
        for pat in CLAUSE:
            if pat.search(new):
                clauses.append(pat.search(new).group(0).strip())
                new = pat.sub(" [clause redacted]", new)
        kept.append(new)
    return "\n".join(kept).strip() + "\n", dropped, clauses


def main():
    key_rows = []
    for spec in SPECIALISTS:
        parts, missing, dropped_total, clause_total = [], [], 0, 0
        for label in ("W", "X", "Y", "Z"):
            arm, rep = MAPPING[spec][label]
            src = OUT / f"{spec}-{arm}{rep}.md"
            if not src.exists():
                missing.append(f"{label} <- {src.name}")
                continue
            body, dropped, clauses = redact(src.read_text(encoding="utf-8"))
            dropped_total += len(dropped)
            clause_total += len(clauses)
            for d in dropped:
                print(f"  [{spec} {label}] dropped line: {d[:90]}")
            for c in clauses:
                print(f"  [{spec} {label}] redacted clause: {c[:90]}")
            parts.append(f"=== OUTPUT {label} ===\n\n{body}")
            key_rows.append(f"{spec},{label},{arm},{rep}")

        if missing:
            print(f"!! {spec}: MISSING {', '.join(missing)} -- bundle written incomplete")

        (JUDGE / f"judge-in-{spec}.md").write_text(
            "\n\n".join(parts) + "\n", encoding="utf-8"
        )
        left = sum(bool(META.search(p)) for p in parts)
        leftc = sum(1 for p in parts for pat in CLAUSE if pat.search(p))
        print(f"{spec}: {len(parts)} of 4 bundled, {dropped_total} lines dropped, "
              f"{clause_total} clauses redacted, residual META {left} / CLAUSE {leftc}")

    (S / "label-key-frontier.csv").write_text(
        "specialist,label,arm,rep\n" + "\n".join(key_rows) + "\n", encoding="utf-8"
    )
    print(f"\nlabel key -> {S / 'label-key.csv'} (never goes to a judge)")
    print(f"judge inputs -> {JUDGE}")


if __name__ == "__main__":
    main()
