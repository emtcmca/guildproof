"""Call the Gemini REST API with exactly one system prompt and one user message.

Why this exists: an eval arm must not be able to see the experiment it is part of. An
agent CLI (Codex's interactive mode, Gemini CLI, or a Claude Code subagent) carries its
own context: config files, project rules, tool output, and in the Claude Code workflow
harness, the parent conversation's latest user message. That last one already contaminated
two cells of a real run. A bare HTTPS call has no such channel, so isolation stops being a
rule the harness is asked to respect and becomes a property of the transport.

Zero dependencies: urllib from the standard library. No SDK, no config file, no state.

Usage:
    python gemini-call.py --system <file> --user <file> --out <file> [--model <id>]
    python gemini-call.py --list-models
    python gemini-call.py --selftest

The key is read from GEMINI_API_KEY (or GOOGLE_API_KEY) and is never printed, never
written to the output file, and never included in an error message.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
# Pinned, never a "-latest" alias: an alias silently changes what a published number
# was measured on. Verified present in this key's model list on 2026-09-19.
DEFAULT_MODEL = "gemini-3.1-pro-preview"


def get_key():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit(
            "ERROR: no API key found.\n"
            "Set GEMINI_API_KEY as a user environment variable, then open a new shell.\n"
            "This script never prints the key's value."
        )
    return key


def post(url, payload, key):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"x-goog-api-key": key, "content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:600]
        # The key travels in a header, not the URL, so it cannot appear in this text.
        sys.exit(f"ERROR: HTTP {e.code} from Gemini.\n{body}")
    except urllib.error.URLError as e:
        sys.exit(f"ERROR: could not reach Gemini: {e.reason}")


def get(url, key):
    req = urllib.request.Request(url, headers={"x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: HTTP {e.code}\n{e.read().decode('utf-8','replace')[:400]}")


def list_models(key):
    data = get(f"{API_ROOT}/models", key)
    rows = []
    for m in data.get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            rows.append((m["name"].replace("models/", ""), m.get("inputTokenLimit", "?")))
    for name, lim in sorted(rows):
        print(f"  {name}  (input limit {lim})")
    print(f"\n{len(rows)} models support generateContent")


def generate(model, system_text, user_text, key):
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        # Deterministic-ish. Recorded in the run doc so the setting is auditable.
        "generationConfig": {"temperature": 1.0, "maxOutputTokens": 8192},
    }
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}

    data = post(f"{API_ROOT}/models/{model}:generateContent", payload, key)

    cands = data.get("candidates") or []
    if not cands:
        sys.exit(f"ERROR: no candidates returned. Raw response:\n{json.dumps(data)[:600]}")
    c = cands[0]
    parts = (c.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        # A blocked or truncated response must fail loudly rather than write an empty
        # arm file that later reads as "the model produced nothing of substance".
        sys.exit(
            f"ERROR: empty text. finishReason={c.get('finishReason')!r}. "
            f"An empty arm is unmeasured, not clean.\n{json.dumps(data)[:600]}"
        )
    return text, data.get("usageMetadata", {}), c.get("finishReason")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", help="file holding the system prompt; omit for a bare arm")
    ap.add_argument("--user", help="file holding the user message")
    ap.add_argument("--out", help="file to write the reply to")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    key = get_key()

    if a.list_models:
        list_models(key)
        return

    if a.selftest:
        # Proves three things at once: the key works, the model id is valid, and the
        # transport carries no ambient context.
        text, usage, _ = generate(
            a.model,
            "Answer in under 25 words.",
            "Can you see any conversation about a project called guildproof, any eval "
            "benchmark, or any message about API keys? Answer yes or no, then name every "
            "piece of context you were given.",
            key,
        )
        print(f"model: {a.model}")
        print(f"reply: {text}")
        print(f"tokens: {usage}")
        return

    if not (a.user and a.out):
        sys.exit("ERROR: --user and --out are required (or use --selftest / --list-models)")

    system_text = open(a.system, encoding="utf-8").read() if a.system else None
    user_text = open(a.user, encoding="utf-8").read()

    text, usage, finish = generate(a.model, system_text, user_text, key)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"wrote {a.out}  ({len(text)} chars, finish={finish}, tokens={usage})")


if __name__ == "__main__":
    main()
