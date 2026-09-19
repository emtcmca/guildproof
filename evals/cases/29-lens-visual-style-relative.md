---
id: "29"
route: lens
command: /guildproof:lens
expected-lenses: [visual-design]
tests: visual-design hard-rule vs style-relative split — a competently executed non-minimal style must not be cross-penalized
---

## Input

```
/guildproof:lens --lens visual-design
```

Artifact under review (a deliberately **brutalist** landing section):

```html
<section style="background:#000; color:#fff; padding:0; font-family:'Courier New',monospace">
  <h1 style="font-size:96px; line-height:0.85; letter-spacing:-0.04em; margin:0;
             text-transform:uppercase; border-bottom:8px solid #fff">
    SHIPPING/<br>IS/THE<br>WHOLE/JOB
  </h1>
  <p style="font-size:15px; line-height:1.6; max-width:62ch; margin:24px 0; color:#d0d0d0">
    We do not do discovery calls. We do not do decks. You describe the problem, we return
    working software in fourteen days or we return the money.
  </p>
  <a href="/start" style="display:inline-block; background:#e8ff00; color:#000; padding:18px 28px;
     font-size:18px; font-weight:700; text-decoration:none; border:4px solid #fff">
    START →
  </a>
  <span style="display:block; margin-top:12px; font-size:11px; color:#4a4a4a">
    Terms apply. Refund excludes third-party costs.
  </span>
</section>
```

## Must

- Judge the style-relative choices **within the brutalist idiom**: the harsh monospace, the
  slashed headline, the 0.85 line-height, the acid-yellow CTA, and the hard borders are a
  coherent executed style, not defects.
- Still flag the genuine **hard-rule** failures — the 11px `#4a4a4a` disclaimer on `#000` fails
  contrast, and 11px is below a readable floor. Hard rules bind regardless of style.
- Name explicitly which findings are hard-rule and which (if any) are style-relative.

## Must not

- **Penalize the artifact for being dense, harsh, high-contrast, uppercase, or non-minimal.**
  Cross-penalizing a committed style against minimal-design convention is the exact regression
  this case exists to catch.
- Recommend softening the palette, lowering the headline size, or adding whitespace as
  *defects* rather than as clearly-labeled optional style alternatives.
- Rewrite the markup (no `--fix` was passed).
