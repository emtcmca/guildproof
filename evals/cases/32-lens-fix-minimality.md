---
id: "32"
route: lens
command: /guildproof:lens
expected-lenses: [accessibility, visual-design]
judge: independent
tests: --fix emits a corrected artifact with minimal targeted changes, and does not drift style-relative choices
---

> **Independent judge required** — this route emits a code artifact. Per `rubric.md`, the
> producer must not grade it.

## Input

```
/guildproof:lens --lens accessibility,visual-design --fix
```

Artifact under review (the case-05 component):

```jsx
<div onClick={() => setOpen(!open)} style={{background:'#1f2430', color:'#3a4150', padding:12}}>
  <span style={{fontSize:11}}>Advanced settings</span>
  {open && <Panel />}
</div>
```

## Must

- Produce findings first, then a corrected component in a copy-pasteable block.
- Fix the real defects: `div onClick` → a real `<button>` (or add `role`/`tabIndex`/key handler),
  `#3a4150` on `#1f2430` fails contrast, 11px is below a readable floor, and the disclosure
  needs `aria-expanded`.
- Changes are **minimal and targeted** — each traceable to a stated finding.
- End with a one-line summary of what changed.

## Must not

- Restyle beyond the findings — don't change the dark palette to a light one, swap the layout,
  rename props, add a design system, or "improve" spacing that was never flagged.
- Invent values that weren't derivable — no invented brand hex, no invented copy, no invented
  component imports. A needed-but-unknown value is a flagged placeholder.
- Drop `<Panel />` or alter the open/close behavior.
- Return findings only, having been passed `--fix`.
