# Tests for `parse_duration(s)`

I wasn't given the implementation, so **no tests were run**. The framework isn't named either. The function name looks like Python, so I picked **pytest**. Everything I had to guess is marked `ASSUMPTION` in the code and listed under Gaps.

## Contract under test

`parse_duration(s: str)` returns the total number of seconds for strings built from hour and minute parts ("1h30m", "45m", "2h"). Input that doesn't fit should raise. The spec doesn't say which exception.

## Cases

**Happy (stated in the spec)**
- Hours and minutes together: `"1h30m"` → 5400
- Minutes only: `"45m"` → 2700
- Hours only: `"2h"` → 7200

**Failure (the spec says invalid input raises)**
- Empty or whitespace-only string
- Text with no duration in it: `"abc"`
- Unit with no number: `"h"`
- Number with an unknown unit: `"1x"`
- Dangling number: `"1h30"`
- Valid duration plus junk on either side: `"1h30m garbage"`, `"garbage1h30m"`. This catches an implementation that searches for a match instead of matching the whole string.
- Non-string input: `None`, `90`, `1.5`, `[]`, `b"1h"`

**Edge (the spec is silent, so each is an assumption)**
- `"30s"` and `"1h30m15s"`. Seconds were never mentioned.
- `"0m"` → 0
- `"90m"` → 5400 (minutes past 59, no rollover required)
- Invalid under the assumed strict reading: `"-5m"`, `"1.5h"`, bare `"30"`, reversed order `"30m1h"`, repeated unit `"1h1h"`

## Tests

```python
"""Tests for parse_duration(s).

Run with:  pytest -q test_parse_duration.py

Sections 1 and 2 pin behavior the spec states or directly implies.
Sections 3 and 4 pin my READING of behavior the spec is silent on. Each row
is tagged ASSUMPTION. If your intended contract differs, delete or flip that
row. Nothing outside section 1 should be treated as verified.
"""
import pytest

# ASSUMPTION: module path. Change to wherever parse_duration lives.
from durations import parse_duration

# ASSUMPTION: "should raise" means ValueError for malformed strings. The spec
# doesn't name a type. I did not use bare `Exception`: it would also pass on a
# NameError or AttributeError from broken code, which is the wrong failure.
INVALID_INPUT = ValueError

# ASSUMPTION: for non-strings, either ValueError or TypeError is acceptable.
INVALID_TYPE = (ValueError, TypeError)


# --- 1. Happy path: the three formats the spec names -------------------------

@pytest.mark.parametrize(
    "text, expected_seconds",
    [
        pytest.param("1h30m", 5400, id="hours-and-minutes"),
        pytest.param("45m", 2700, id="minutes-only"),
        pytest.param("2h", 7200, id="hours-only"),
    ],
)
def test_returns_total_seconds_for_specified_formats(text, expected_seconds):
    # Distinct values per case: 1h30m only equals 5400 if h=3600 and m=60,
    # so a swapped or wrong unit multiplier fails here.
    assert parse_duration(text) == expected_seconds


# --- 2. Failure: clearly malformed input must raise --------------------------

@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty-string"),
        pytest.param("   ", id="whitespace-only"),
        pytest.param("abc", id="no-duration-at-all"),
        pytest.param("h", id="unit-without-number"),
        pytest.param("m", id="minute-unit-without-number"),
        pytest.param("1x", id="unknown-unit"),
        pytest.param("1h30", id="dangling-number-after-valid-part"),
        pytest.param("1h30m garbage", id="trailing-junk-after-valid-duration"),
        pytest.param("garbage1h30m", id="leading-junk-before-valid-duration"),
    ],
)
def test_raises_on_malformed_string(text):
    with pytest.raises(INVALID_INPUT):
        parse_duration(text)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="None"),
        pytest.param(90, id="int"),
        pytest.param(1.5, id="float"),
        pytest.param([], id="list"),
        pytest.param(b"1h", id="bytes"),
    ],
)
def test_raises_on_non_string_input(value):
    # ASSUMPTION: non-strings count as invalid input. Spec says "invalid
    # input should raise" and doesn't distinguish type errors from format errors.
    with pytest.raises(INVALID_TYPE):
        parse_duration(value)


# --- 3. Edge behavior the spec doesn't state (ASSUMPTION rows) ---------------

@pytest.mark.parametrize(
    "text, expected_seconds",
    [
        pytest.param("30s", 30, id="ASSUMPTION-seconds-unit-supported"),
        pytest.param("1h30m15s", 5415, id="ASSUMPTION-h-m-s-combined"),
        pytest.param("0m", 0, id="ASSUMPTION-zero-is-valid-not-an-error"),
        pytest.param("90m", 5400, id="ASSUMPTION-minutes-over-59-not-rejected"),
    ],
)
def test_assumed_edge_values(text, expected_seconds):
    assert parse_duration(text) == expected_seconds


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("-5m", id="ASSUMPTION-negative-duration-invalid"),
        pytest.param("1.5h", id="ASSUMPTION-fractional-invalid"),
        pytest.param("30", id="ASSUMPTION-bare-number-without-unit-invalid"),
        pytest.param("30m1h", id="ASSUMPTION-units-out-of-order-invalid"),
        pytest.param("1h1h", id="ASSUMPTION-repeated-unit-invalid"),
    ],
)
def test_assumed_invalid_shapes_raise(text):
    with pytest.raises(INVALID_INPUT):
        parse_duration(text)
```

## Self-challenge

- **Wrong multipliers (h=60, m=3600) or a swap.** Caught by `1h30m`, `45m` and `2h`, because each expects a different value.
- **Parsing only the last or first component.** Caught by `1h30m`.
- **`re.search` in place of a full match.** Caught by the leading and trailing junk cases. This is the failure most likely to slip through.
- **Returning 0 or `None` on bad input instead of raising.** Caught by every `pytest.raises` case.
- **Raising the wrong thing on garbage (a bug's `NameError`).** Caught, because I assert `ValueError` and not `Exception`.
- **Gap I fixed:** `whitespace-only` was missing. `int("")`-style implementations often raise on `""` but accept `"   "`.
- **Still unpinned:** the exact exception class. The suite is only as strict as `INVALID_INPUT`.

## Gaps

1. **Exception type is unspecified.** If it's a custom error such as `DurationError`, change `INVALID_INPUT`. It's a single line.
2. **Not tested, because the spec is silent and I won't guess:**
   - Uppercase units (`"1H30M"`)
   - Padded whitespace (`" 1h30m "`)
   - Unicode digits (Python's `\d` and `int()` accept `"١h"`). This one deserves a decision from you, since a regex-based parser can accept it without meaning to.
   - Very large values
3. **Return type** (int versus float) isn't asserted. `5400 == 5400.0` in Python, so the tests can't tell them apart. If callers need an `int`, add `assert isinstance(..., int)`.
4. **Not executed.** No implementation was supplied, so I couldn't confirm that the suite goes red on a deliberately broken version. Before trusting it, run it against a mutant. `re.search` in place of `fullmatch` is the first one to try.
5. **Import path is invented** (`durations`). Point it at the real module.

If the section 3 assumptions are wrong for your intended behavior, send the contract or the implementation and I'll rewrite those rows against something verified.