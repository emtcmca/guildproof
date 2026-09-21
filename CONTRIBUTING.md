# Contributing

guildproof is prompts, not code. That changes what a good contribution looks like: the
highest-value thing you can send is **a real bad output**, because it can become a test case.

## The most useful contribution

A prompt that produced a weak, wrong, or overconfident result — with the input, the output, and
what specifically was wrong with it. There is an issue template for exactly this.

`evals/` is a 38-case regression suite with 6 deliberately-broken calibration fixtures
(`evals/known-bad/`) that the suite must always FAIL. That corpus exists because nine straight
all-PASS runs are indistinguishable from a broken judge. It still misses things. A concrete
defect you hit is how it stops missing that one.

## Where changes go

| You want to change | Where |
|---|---|
| A command, agent, lens, or template | here, in this repo |
| The skills published for non-Claude-Code agents | here — [guildproof-skills](https://github.com/emtcmca/guildproof-skills) is generated from this repo and never hand-edited |
| Install or packaging for `npx skills add` | [guildproof-skills](https://github.com/emtcmca/guildproof-skills/issues) |

A fix made directly in the mirror is overwritten the next time it regenerates, and its CI fails
on the drift in the meantime. Fix the prompt here and the mirror picks it up.

## Adding a lens

You do not need a fork or a PR to use your own lens — drop a markdown file in
`~/.claude/guildproof-lenses/` and `/lens` will find it. See "Add your own lens" in the README.

Send a PR only if the lens is general enough that a stranger would want it. A lens that encodes
one team's house style is a local file, not a repo change.

## Adding or changing an agent

Every gallery agent has a `description` in its frontmatter — that is the field a host uses to
auto-select it by task context, and an agent without one cannot be invoked automatically. All 20
of them were shipped missing it once; a clean-install smoke test caught it in 30 seconds after
two code reviews did not. Do not add an agent without one.

Agents are also held to an honesty floor: no fabricated facts, citations, or MCP servers, and an
explicit refusal path when the request is under-specified. An agent that confidently produces
something plausible from a thin request is the failure mode this repo exists to avoid.

## Pull requests

There is a [PR template](.github/pull_request_template.md) that asks for the below; it is a
reminder, not a form, and a one-line PR is fine.

- One concern per PR.
- If you changed a prompt, say what you ran it against and what changed in the output. "Should
  be better" is not reviewable.
- No dependencies. No API keys. No model calls. Zero-dependency is architectural here, not a
  preference — the whole thing is method and structure, and the host agent does the reasoning.
- Run `node scripts/validate.mjs` and `node scripts/validate.mjs --selftest`. Both spend nothing —
  no model call, no key, no network. CI runs them too, in `fresh-machine.yml`.
- **Counts go on a ref.** If you state one in a doc, take it with `git ls-tree`, not from your
  working directory. This repo has published a wrong count in both directions more than once, and
  every instance traced to counting files in a checkout that was sitting on a different branch.

## Claiming that a prompt works

Contributing a prompt needs none of this. **Claiming a prompt causes an effect needs a reduced
arm** — a cheaper version of the same prompt, run as its own arm, to show the effect is not simply
coming from the formatting.

That rule was bought the hard way: a third arm carrying only one section of `agents/verifier.md`
reproduced that prompt's entire published advantage, which retired a headline number.
[`docs/FINDINGS.md`](docs/FINDINGS.md) has the full account under "Construct validity".

## Security

Do not report a vulnerability in a PR or a public issue. [`SECURITY.md`](SECURITY.md) has the private
channel and the scope.

## Code of conduct

[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Argue with the work, not the person.

## License

Apache-2.0. Contributions are accepted under the same license.
