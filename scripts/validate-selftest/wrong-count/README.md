# fixture

A deliberately tiny plugin used only to prove `scripts/validate.mjs` can fail.

- **2 commands**, a 9-agent gallery, and 2 lenses.
- The eval suite is 3 cases plus 6 known-bad fixtures the suite must always fail.

## Install

Copy 2 things into your `~/.claude/` directory:

| Copy this | To here |
|---|---|
| `commands/` | `~/.claude/commands/` |
| `agents/` | `~/.claude/fixture-agents/` |

## Gallery

A roster of 3 specialists:

- **Build:** `alpha-writer` · `gamma-planner`
- **Review:** `beta-checker`

## Lenses

The 2 lenses:

| Lens | Applies to |
|---|---|
| `first-lens` | things |
| `second-lens` | other things |

Force one with `/fixture:lens something --lens first-lens`.
