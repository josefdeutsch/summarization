# Curator {{CASE_ID}} — {{CASE_TITLE}} (Float-only Python Graders)

This guide mirrors the Curator grader style used in A.4/A.6 and is intended as a reusable template for future cases (e.g., A.7).

## What this test framework does (brief)

This guide defines a deterministic, float-only test framework for Curator outputs.

**Goal:** enforce machine-parseable structure, exact count behavior, and case-specific quality constraints while keeping debugging simple and stepwise.

---

## Chat prompt (Takeaway Curator)

Declare the following prompt as `systemmessage`:

### systemmessage
```text
You are Takeaway Curator.

Your responsibility is to extract structured, information-rich takeaways from a book using FileSearch.

Core behavior
- Follow the requested chapter scope exactly (e.g., "Chapter 2" or ["Chapter 2", "Chapter 3", "Chapter 4"]).
- Do not require a numeric page interval from the user.
- Prefer depth within a concept and keep each takeaway locally coherent.
- Each takeaway must map to exactly one contiguous page span.

Quality rules
- Select central, non-trivial insights.
- Avoid generic advice, repetition, and padding.
- Avoid phrasing like "the author says".

Range rules
- approx_page_range must be formatted exactly as: p<start>-<end>
- Example valid: p82-85
- Example invalid: p82-p85, 82-85, p82–85, p82 - 85

Output contract (strict)
- Output JSON only (no markdown, no prose).
- Use exactly this schema:
{
"takeaways": [
{
"id": "T1",
"title": "Short H3-style heading",
"claim": "One-sentence core insight",
"scope_keywords": ["keyword1", "keyword2"],
"approx_page_range": "p82-85"
}
]
}

Self-check before responding
1) All takeaways belong to the requested chapter scope (single chapter or chapter list).
2) Every takeaway has exactly one contiguous approx_page_range.
3) Range format is p<start>-<end>.
4) JSON is valid and schema-complete.
```

### usermessage
```text
{{PLACEHOLDER_USERMESSAGE_FOR_CASE}}
```

---

## 1) Python grader contract (critical)

- Return float only: `1.0` PASS, `0.0` FAIL.
- Use `def grade(sample, item):`.
- Read output from `sample.get("output_text", "")`.
- Parse with `json.loads(output_text)`.
- Do not return dicts in this guide.

---

## 2) Runtime mapping: `sample` vs `item`

- `sample`: model output payload (`output_text`, `output_json`, `choices`, ...)
- `item`: dataset row for expected eval behavior (`expected_takeaway_count`, case-specific fields, ...)

Typical pattern:

```python
output_text = sample.get("output_text", "")
expected_n = int(item.get("expected_takeaway_count", 0))
```

---

## 3) Dataset fields (template)

Use base fields:
- `case_id`
- `input`
- `expected_takeaway_count`

Add case-specific fields:
- `{{CASE_FIELD_1}}`
- `{{CASE_FIELD_2}}`
- `{{CASE_FIELD_3_OPTIONAL}}`

Example:

```json
{
  "case_id": "{{CASE_ID}}",
  "input": "{{USER_INSTRUCTION}}",
  "expected_takeaway_count": 8,
  "{{CASE_FIELD_1}}": "{{VALUE}}",
  "{{CASE_FIELD_2}}": "{{VALUE}}"
}
```

---

## 4) Case logic (ACTUAL vs EXPECTED)

Define clearly:
- EXPECTED behavior from dataset fields.
- ACTUAL behavior from parsed output (`takeaways[*].approx_page_range` and required keys).
- Hard floor threshold (immediate fail condition).
- Soft quality threshold (`N-1` rule or equivalent).

Template math block:

- `{{INTERMEDIATE_METRIC_1}} = ...`
- `{{INTERMEDIATE_METRIC_2}} = ...`
- `{{QUALITY_RATIO}} = ...`

Recommended rule:
- fail if any takeaway violates hard floor (`{{HARD_FLOOR_RULE}}`)
- pass if at least `expected_n - 1` takeaways satisfy soft quality (`{{SOFT_QUALITY_RULE}}`)

---

## 5) Main grader — {{CASE_MAIN_TEST_NAME}}

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def grade(sample, item):
    """Return 1.0 when output matches schema/count and {{CASE_LOGIC_SUMMARY}}."""
    output_text = sample.get("output_text", "")

    try:
        obj = json.loads(output_text)
    except Exception:
        return 0.0

    if not isinstance(obj, dict):
        return 0.0

    takeaways = obj.get("takeaways")
    if not isinstance(takeaways, list):
        return 0.0

    try:
        expected_n = int(item["expected_takeaway_count"])
        # Case-specific expected values:
        # x = item["{{CASE_FIELD_1}}"]
        # y = item["{{CASE_FIELD_2}}"]
    except Exception:
        return 0.0

    if expected_n < 1:
        return 0.0

    if len(takeaways) != expected_n:
        return 0.0

    strong = 0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0

        for k in REQUIRED_KEYS:
            if k not in t:
                return 0.0

        rng = t.get("approx_page_range", "")
        if not isinstance(rng, str):
            return 0.0

        m = RANGE_RE.match(rng)
        if not m:
            return 0.0

        A, B = int(m.group(1)), int(m.group(2))
        a, b = min(A, B), max(A, B)
        span = b - a + 1

        # TODO: Insert case hard-floor logic
        # if {{HARD_FAIL_CONDITION}}:
        #     return 0.0

        # TODO: Insert case soft-quality logic
        # if {{STRONG_CONDITION}}:
        #     strong += 1

    return 1.0 if strong >= expected_n - 1 else 0.0
```

---

## 6) Split debug tests (small graders, float-only)

Use these as separate tests in OpenAI Evals Web UI to isolate failures.

### Test 1 — JSON Parse Validity
- Parses `sample["output_text"]` with `json.loads`.

### Test 2 — Root Object + Takeaways Array
- Requires root dict and `takeaways` list.

### Test 3 — Required Field Presence
- Enforces required keys for each takeaway.

### Test 4 — Expected Dataset Configuration
- Validates `expected_takeaway_count` and case-specific config fields.

### Test 5 — Exact Takeaway Count Match
- Requires `len(takeaways) == expected_takeaway_count`.

### Test 6 — Page Range Format Validation
- Requires `approx_page_range` to match `^p([0-9]+)-([0-9]+)$`.

### Test 7 — Hard Floor Rule
- Isolates the immediate fail threshold (`{{HARD_FLOOR_RULE}}`).

### Test 8 — Soft Quality Rule
- Isolates aggregate quality threshold (often `>= 0.8 for N-1`, or case equivalent).

---

## 7) Recommended debug order

1. Test 1 — JSON Parse
2. Test 2 — Root + list
3. Test 3 — Required fields
4. Test 4 — Dataset config
5. Test 5 — Count match
6. Test 6 — Range format
7. Test 7 — Hard floor
8. Test 8 — Soft quality

This order isolates syntax, schema, config, and case-logic failures progressively.

---

## 8) Case author checklist

Before shipping a new case guide (example: A.7):
- Replace all `{{PLACEHOLDERS}}`.
- Keep system prompt consistent with Curator core unless capability changed.
- Ensure dataset fields in section 3 exactly match code in section 5.
- Verify debug tests cover every failure mode in the main grader.
- Run all tests in OpenAI Evals Web UI and record pass/fail behavior.
