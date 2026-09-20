<!--
PROOF ASSET — answer-delta side-by-side. Source content for the README hero image/GIF.

Purpose: answer the visitor's real question — "is this better than what I'd type myself?" —
BEFORE they install. The delta that sells is answer -> answer, not prompt -> prompt. A
prompt-only before/after reads as bloat; this shows the naive prompt's honest answer shipping a
real bug, and the sharpened prompt's answer catching it.

HONESTY NOTE (load-bearing): the "before" answer is a FAIR answer to the naive prompt — a
competent, backoff-aware retry function, not a rigged strawman. It fails on the one thing the
naive prompt could not tell the model: whether the call is safe to retry. That is a true,
defensible delta, and it is the honesty floor made concrete — the sharpened run flags the
decision it cannot know rather than guessing.

Task chosen: generic-dev, universally relatable, and the naive answer's flaw is invisible until
production (a retried non-idempotent POST = a double charge).

Render targets:
  - Static side-by-side PNG (the workhorse — skims into HN/LinkedIn/dev.to)
  - README-top GIF that plays the four beats
Both draw from the four panels below.
-->

# guildproof — the answer delta

*Same model. Same task. The only thing that changed is the prompt.*

---

## PANEL 1 — what you type

```
write a function to retry a failed API call
```

## PANEL 2 — the answer that request gets (honest, unprompted)

```js
async function retry(fn, attempts = 3, delayMs = 500) {
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      await new Promise(r => setTimeout(r, delayMs * 2 ** i)); // exponential backoff
    }
  }
  throw lastErr;
}
```

Looks complete. It even backs off exponentially. Ship it, and here is the bug it carries:
it **retries every failure the same way** — including a `POST /charge` that already succeeded on
the server but timed out on the wire. That is a **double charge**. It also retries `400`s and
`403`s that will never succeed, burning the budget and the rate limit on requests that are
dead on arrival. The prompt never said the call was safe to retry, so the model assumed it was.

---

## PANEL 3 — the same task, sharpened first

```
/guildproof:sharpen write a function to retry a failed API call
```

→ returns a prompt with the decisions the one-liner left unstated (abridged):

```
ROLE: a backend engineer who treats every retry as a correctness decision, not a loop.
OBJECTIVE: retry a failed API call ONLY when retrying is safe and can succeed.

REQUIREMENTS:
- Retry only retryable failures: network errors, timeouts, 429, and 5xx. Never retry 4xx
  (except 429) — they will not succeed and waste the budget.
- Exponential backoff WITH jitter, to avoid a synchronized retry storm (thundering herd).
- A total deadline / max elapsed time, not just a max attempt count.
- Honor a Retry-After header on 429/503 when present.

PROHIBITIONS (must NOT do):
- Do NOT retry a non-idempotent request (a bare POST that creates or charges) unless the
  caller supplies an idempotency key — retrying a POST that already succeeded double-acts.
- Do NOT swallow the final error; surface which attempts failed and why.

OPEN QUESTION (answer before building):
- Is this call idempotent, or does it carry an idempotency key? The retry is only safe if yes.
  I will not guess this — it is the difference between a resilient client and a double charge.
```

## PANEL 4 — the answer THAT prompt gets

```js
// Retries only when it is safe AND can succeed. Idempotency is the caller's to assert —
// the prompt refused to guess it, so the signature makes it explicit.
async function retry(fn, {
  maxAttempts = 4,
  deadlineMs = 10_000,
  idempotent = false,          // MUST be true (or carry an idempotency key) to retry writes
  isRetryable = defaultRetryable,
} = {}) {
  const start = Date.now();
  let attempt = 0, lastErr;
  while (attempt < maxAttempts && Date.now() - start < deadlineMs) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (!isRetryable(err) || !idempotent) throw err;   // non-retryable OR unsafe: stop now
      const retryAfter = err.retryAfterMs ?? 0;
      const backoff = Math.min(2 ** attempt * 200, 2000);
      const jitter = backoff * (0.5 + Math.random() * 0.5); // full-ish jitter, no storm
      await new Promise(r => setTimeout(r, Math.max(retryAfter, jitter)));
      attempt++;
    }
  }
  throw lastErr;
}

function defaultRetryable(err) {
  if (err.code === 'ECONNRESET' || err.code === 'ETIMEDOUT') return true;
  const s = err.status;
  return s === 429 || (s >= 500 && s <= 599);   // never 4xx except 429
}
```

Same model. Same task. The naive prompt got a function that double-charges; the sharpened
prompt got one that refuses to retry a write it was never told is safe — and said so out loud
instead of guessing.

---

## The caption (for the image / post)

> **You already know how to write the good version. The tool is that you don't have to remember
> to, every time.** guildproof made the model surface the idempotency decision, the retryable-only
> rule, and the jitter — the invisible scaffolding a senior engineer adds and a one-liner skips.
> It never invented the answer to "is this call idempotent?" — it flagged it. That refusal to
> guess is the whole point.

<!--
Why this asset works where a prompt-only before/after fails:
- It shows the ANSWER getting better, not just the prompt getting bigger (kills the "bloat" read).
- The before is a FAIR, competent answer with a hidden production bug — not a strawman.
- The delta is a bug a skeptic recognizes instantly (retried POST = double charge).
- It demonstrates the honesty floor in a way a visitor can feel: the sharpened run refuses to
  guess the one fact it cannot know, and says so.
Do NOT swap the before-answer for a dumber one to widen the delta. The fairness is the credibility.
-->
