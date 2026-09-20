---
id: "05"
route: lens
command: /guildproof:lens
expected-lenses: [accessibility, visual-design, ux-designer]
tests: findings map to lens checklist, specificity (quotes the artifact), worst-first
---

## Input

```
/guildproof:lens --lens accessibility,visual-design
```

Artifact under review (pasted with the command):

```jsx
function SaveBar({ saving }) {
  return (
    <div style={{ background: "#1f2430", padding: 6 }}>
      <span style={{ color: "#3a4150", fontSize: 11 }}>Unsaved changes</span>
      <div onClick={save} style={{ color: "#6b7280", cursor: "pointer" }}>
        {saving ? "..." : "Save"}
      </div>
    </div>
  );
}
```

## Must

- Flag the real defects: `#3a4150` text on `#1f2430` fails contrast; the Save control is a
  `div onClick` (not a button — not keyboard-operable, no focus state, no role); 11px text;
  no disabled/feedback state while `saving`.
- Findings prefixed ✅/⚠️/❌, worst-first, and **quote the actual values/lines**.
- Map each finding to the named lens's checklist (accessibility, visual-design).
- End with top-3 fixes by impact + the `/guildproof:sharpen` offer.

## Must not

- Rewrite the component (this is /lens — findings only).
- Pad with ✅ flattery that isn't a real check.
