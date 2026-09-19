---
id: "31"
route: lens
command: /guildproof:lens
expected-lenses: [ai-tells, editorial]
tests: the ai-tells / voice-preservation collision — strip filler without flattening a deliberate authorial signature
---

## Input

```
/guildproof:lens --lens ai-tells,editorial --fix
```

Artifact under review (a newsletter section with a **deliberate** style — short fragments, an
em-dash motif, a recurring sign-off, plus real filler that should go):

```
Fourteen years of property management taught me one thing. Systems beat heroics.

Not talent. Not hustle. Systems.

I want to leverage this opportunity to delve into what that actually means in practice —
because in today's landscape, everyone says "process" and almost nobody means it. A process is
not a document. It's the thing that happens when you're not in the room.

Here's the test — and it's a robust one. Take the person who knows the most. Remove them for two
weeks. What breaks?

That's your system. Everything else is a comprehensive, holistic story you tell yourself.

Fix what breaks. Then break it again.

— E.
```

## Must

- Cut the genuine tells: `leverage this opportunity`, `delve into`, `in today's landscape`,
  `robust`, and the `comprehensive, holistic` cluster.
- **Preserve the authorial signature** — the one-line fragments ("Not talent. Not hustle.
  Systems."), the em-dash motif, the imperative close ("Fix what breaks. Then break it again."),
  and the `— E.` sign-off all survive the fix intact.
- Where a change would alter voice rather than remove a tell, **flag it as a suggestion and
  leave the text alone**, saying so explicitly.
- Run the second pass in both directions — confirm no new tells *and* no over-stripping.

## Must not

- **Flatten the fragments into complete sentences, regularize the em-dashes, or drop the
  sign-off.** That is the failure this case exists to make falsifiable: `ai-tells` strips
  aggressively and must not homogenize a distinctive author.
- Treat the deliberate repetition ("Not talent. Not hustle. Systems.") as AI-style anaphora.
- Rewrite wholesale rather than making minimal targeted changes.
