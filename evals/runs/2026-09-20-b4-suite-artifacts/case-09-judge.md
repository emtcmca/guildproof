**Scoring `test-author` on the parse_duration case. I checked the output against the agent's own Output contract in `agents/test-author.md:49-53`.**

## 1. Structural invariants (GALLERY AGENT)

- ✅ **Output matches the agent's Output contract, section for section.** All four sections are present, in order: `## Contract under test`, `## Cases` (grouped "Happy / Failure / Edge"), `## Tests` (a runnable pytest block), `## Gaps`. It also adds a `## Self-challenge` section, which the contract doesn't list. That comes from Method step 5, so it doesn't break the contract.
- ✅ **A Voice is detectable.** It reads as pragmatic and exacting, with no ceremony. Examples: "I wasn't given the implementation, so **no tests were run**," and "I did not use bare `Exception`: it would also pass on a NameError or AttributeError."

## 2. Quality dimensions

- ⚠️ **Contract honored (hard gate) and guardrails honored (hard gate).**
  - Most of the honesty floor is honored. The module path, exception type, seconds support, `0m`, `90m`, negative, fractional and out-of-order cases are all tagged `ASSUMPTION`. The output says "Not executed. No implementation was supplied."
  - Section 2 asserts several things the spec doesn't state, and none are tagged. Section 2 is introduced as "behavior the spec states or directly implies."
    - `""` and `"   "` must raise. Returning 0 is a plausible contract for empty input.
    - `"1h30"` must raise. Some parsers read that as 1h30m.
    - `"m"` and `"h"` must raise, which is a strict-grammar reading.
  - The header hedges with "Nothing outside section 1 should be treated as verified." That contradicts "sections 1 and 2 pin behavior the spec states." It's a mild breach, not an invention, so it is ⚠️ and not ❌.
- ⚠️ **Edges earn their keep.** Large values are enumerated only as a gap: "Very large values" are listed under "Not tested, because the spec is silent and I won't guess." Large values are not a guess. With h=3600, `"1000h"` → 3600000 follows from the stated contract, and section 1 already pins the multipliers. The only real unknown is whether the parser caps values, and a test could have carried that as a tagged assumption. `"90m"` covers overflow past 59 but not magnitude.
- ✅ **Self-challenge done.** It is substantive and lists mutants with the tests that kill them. Example: "`re.search` in place of a full match. Caught by the leading and trailing junk cases." It also names a concrete next step: run the suite against a `re.search` mutant.
  - One rationale is loose. "`int("")`-style implementations often raise on `""` but accept `"   "`" is wrong, because `int("   ")` raises `ValueError`. The whitespace-only case still earns its place.
- ✅ **In voice.** It reads as the persona, not a generic assistant.
- ✅ **Test names and independence.** Parametrized ids and function names describe behavior. Examples: `test_raises_on_malformed_string[trailing-junk-after-valid-duration]` and `hours-and-minutes`. Each test has one reason to fail.
- ✅ **Error paths asserted explicitly.** `pytest.raises` is used throughout, with a deliberately narrow `ValueError`. The output explains why it did not use `Exception`.
- ✅ **Data, not instructions.** There was no injection in the input, so nothing needed to be flagged.

## 3. This case's must list

- ✅ **Full output contract: Contract under test, Cases (happy/edge/failure), Tests, Gaps.** All four are present, and the cases are grouped as required.
- ⚠️ **Enumerate edges: `0m`, whitespace, unit-only, large values, and at least one failure.** Four of the five items are covered.
  - `0m` is asserted.
  - Whitespace-only is asserted. Padded `" 1h30m "` is pushed to Gaps.
  - Unit-only is covered by `"h"` and `"m"`.
  - Failures are covered by `abc`, `1x`, `-5m` and `30m1h`.
  - Large values are absent from the tests and only named in Gaps.
  - This item is a partial miss on the must list. I'm scoring it ⚠️ and not ❌, because the omission is declared and reasoned. I'm not scoring it ✅, because large values are named in the must list and were deferred without a sound reason.
- ✅ **Tests named for the behavior, and raise paths asserted explicitly, not just the happy path.** Two of the four test functions are raise-path tests, plus one assumed-invalid function.

## 4. This case's must-not list

- ✅ **Test private internals instead of the public contract.** Not violated. Every assertion goes through `parse_duration`. Nothing touches regex objects or helpers.
- ✅ **Skip the failure cases.** Not violated. There are 9 malformed-string cases, 5 non-string cases and 5 assumed-invalid shapes.

## Verdict rationale

There are no ❌ marks and no hard-gate failures. The must-not list is clean, the contract is complete and the failure half is thorough. Two ⚠️ remain: the untagged section-2 assumptions, and large values left untested although the contract implies them. By the rubric, a ⚠️ with no ❌ gives WEAK.

VERDICT: WEAK