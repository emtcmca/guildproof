# Security policy

## Reporting a vulnerability

**Use GitHub's private vulnerability reporting:**
[Report a vulnerability](https://github.com/emtcmca/guildproof/security/advisories/new).
That channel is private until an advisory is published. **Please do not open a public issue for a
vulnerability**, and please do not post a working exploit in one.

If private reporting is unavailable to you, open an issue titled `security contact request` with no
detail in it, and you will be given somewhere private to send the report.

Include, as much as you have: what an attacker gains, the smallest input that shows it, which file or
prompt is involved, and whether it needs the plugin installed or reproduces from the skills mirror
too.

**Expect a first response within 7 days.** This is a one-person project with no users and no paid
support, so that is a good-faith target and not a service commitment. If a report is valid, you will
be credited in the advisory and the CHANGELOG unless you ask not to be.

## Supported versions

Only the tip of `main` and the newest tag. There are no maintained release branches, no backports,
and no LTS. If a fix matters to you, take it from `main`.

| Version | Supported |
|---|---|
| `main` | yes |
| newest tag | yes |
| anything older | no |

## What is in scope

guildproof ships **prompts**, not a running service. There is no server, no database, no network
listener, and the plugin makes **no model calls of its own** — your agent does. That shapes what a
vulnerability here even looks like. In scope:

- **Prompt injection that changes behavior.** An artifact, lens file, or request that gets a
  guildproof agent to follow instructions embedded in data it was asked to *review*. The repo ships
  `KB2`, a fixture where a review obeys a planted injection and clears the artifact, precisely
  because this is the failure class that matters most here.
- **A verdict that can be laundered.** Anything that makes the verifier report a non-blocking verdict
  on a defect it actually found, or claim independence it does not have. `KB4` is the fixture for
  this, and `case-34` is the committed counterexample for the halt condition.
- **Secret or file exfiltration.** A prompt that induces an agent to read outside its stated scope or
  to echo credentials it encountered.
- **Path handling in the harness scripts** under `evals/harness/` and `scripts/`, which do read and
  write real files.
- **A guardrail that does not hold.** If something `agents/` or `docs/SECURITY.md` claims is
  structurally prevented turns out to be reachable, that is a valid report even with no exploit —
  a claim that does not hold is the defect.

## What is out of scope

- **What your model decides to do.** These are prompts. A model can ignore any instruction in them,
  and a stronger model is not a security boundary. If the issue is "the model did something
  unhelpful," that is a prompt-quality issue — there is an
  [issue template](.github/ISSUE_TEMPLATE/prompt-quality.yml) for it.
- **Anything requiring an attacker who can already commit to your repo or write your `~/.claude/`.**
  Project-local lens files are explicitly a trusted-input surface; `docs/SECURITY.md` says so under
  the threat model. Someone who can plant a lens can plant a hook, and that is a property of your
  repo's access control.
- **Missing hardening with no reachable impact**, and third-party issues in Claude Code, Codex, or any
  host. Report those upstream.
- **The eval numbers.** A disputed measurement is not a vulnerability. Those belong in a normal issue,
  and [`docs/FINDINGS.md`](docs/FINDINGS.md) states what each one does and does not support.

## The threat model itself

The reasoning, the adversary this was designed against, and the guardrails that close each path live
in **[`docs/SECURITY.md`](docs/SECURITY.md)**. Read that before reporting: it will tell you whether
what you found is a known accepted limit or something new. It is also the document to attack — if it
overstates a guarantee, that is worth a report.
