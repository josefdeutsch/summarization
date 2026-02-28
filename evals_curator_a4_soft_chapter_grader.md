# Curator A.4 — Soft Chapter Scope Grading (Float-only Python Graders)

This rewrite applies the clarified contract:
- Python graders return **float only** (`1.0` PASS, `0.0` FAIL).
- Use `def grade(sample, item):`.
- Read model output from `sample.get("output_text", "")`.
- Parse JSON from text with `json.loads(output_text)`.


## What this test framework does (brief)

This guide defines a deterministic, float-only test framework that checks whether Curator outputs stay within the expected chapter scope while preserving required schema and exact takeaway count.

**Goal:** catch scope drift early (cross-chapter leakage), enforce machine-parseable structure, and provide a step-by-step debug path from parse errors to overlap-quality failures.

---

## Chat prompt (Takeaway Curator)

Declare the following prompt as `systemmessage`:

### systemmessage
```text
You are Takeaway Curator.

Your responsibility is to extract structured, information-rich takeaways from a book using FileSearch.

Workflow requirements
- Use FileSearch to inspect the source before producing takeaways.
- If the user provides chapter scope, treat it as a hard boundary.
- If no scope is provided, operate over the full book.

Content quality requirements
- Select central, non-trivial insights.
- Prefer depth within one concept over broad, shallow summaries.
- Avoid minor observations, repetition, padding, and phrases like "the author says".

Page citation requirements (critical)
- Each takeaway must include `approx_page_range`.
- Each takeaway must use exactly one contiguous page range.
- Do not combine multiple ranges in one takeaway.
- If scope is provided, ranges must stay inside that scope.

Range formatting requirements
- `approx_page_range` must be exactly `p<start>-<end>`.

Output contract (strict)
- Return JSON only (no markdown, no prose).
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
1) Output is valid JSON and schema-complete.
2) Takeaway count follows user/dataset requirements.
3) Every takeaway has exactly one contiguous `approx_page_range` in valid format.
4) All ranges are inside requested scope when scope is provided.

```

### usermessage (A.4 — scoped chapter range)
```text
Extract exactly 8 information-rich takeaways from Chapter 2: The interoceptive superhighway, Chapter 3: Power up, and Chapter 4: Gut reading for beginners.
```


### Dataset file (.jsonl) for OpenAI Evals

Use this dataset file: `datasets/evals_curator_a4_usermessage.jsonl`.

```jsonl
{"case_id":"A.4","input":"Extract exactly 8 information-rich takeaways from Chapter 2: The interoceptive superhighway, Chapter 3: Power up, and Chapter 4: Gut reading for beginners.","expected_chapter_start":38,"expected_chapter_end":134,"expected_takeaway_count":8}
```


---

## 1) Python grader contract (critical)

- Return a float in `[0.0, 1.0]`.
- `1.0` means pass.
- `0.0` means fail.
- Do not return dicts in this guide.

---

## 2) Runtime mapping: `sample` vs `item`

- `sample`: model output payload (`output_text`, `output_json`, `choices`, ...)
- `item`: dataset row (`expected_chapter_start`, `expected_chapter_end`, `expected_takeaway_count`, ...)

Typical access pattern:

```python
output_text = sample.get("output_text", "")
expected_n = int(item.get("expected_takeaway_count", 0))
```

---

## 3) Default fallback behavior (`dict.get`)

```python
sample.get("output_text", "")
```
- returns the value if key exists
- otherwise returns `""`

```python
sample.get("output_json", None)
```
- returns the value if key exists
- otherwise returns `None`

The second argument is a fallback default value.

---

## 4) Dataset fields for A.4 soft chapter checks

Use these row fields:
- `case_id`
- `input`
- `expected_chapter_label`
- `expected_chapter_start`
- `expected_chapter_end`
- `expected_takeaway_count`

Example:

```json
{
  "case_id": "A.4",
  "input": "Extract exactly 8 information-rich takeaways from Chapter 2: The interoceptive superhighway.",
  "expected_chapter_label": "Chapter 2 — The interoceptive superhighway",
  "expected_chapter_start": 38,
  "expected_chapter_end": 66,
  "expected_takeaway_count": 8
}
```

---

## 5) Soft-scope principle (ACTUAL vs EXPECTED)

- EXPECTED chapter interval: `[S, E]` from dataset row.
- ACTUAL takeaway interval: parsed from `approx_page_range` (e.g., `p40-42`).
- Overlap ratio per takeaway:
  - `intersection = max(0, min(b, E) - max(a, S) + 1)`
  - `range_len = b - a + 1`
  - `overlap_ratio = intersection / range_len`

Recommended rule:
- fail if any takeaway has `overlap_ratio < 0.5`
- pass if at least `expected_n - 1` takeaways have `overlap_ratio >= 0.8`

---

## 5.1) Multi-chapter expected range (e.g., Chapter 2 + 3 + 4)

If your test case expects several adjacent chapters together, treat them as one expected interval.

Example:
- Chapter 2: `p38-66`
- Chapter 3: `p67-94`
- Chapter 4: `p95-120`
- Combined expected interval: `p38-120`

Suggested dataset fields for this mode:
- `expected_chapter_start` = first page of the first chapter
- `expected_chapter_end` = last page of the last chapter
- `expected_chapter_labels` (optional) = list like `["Chapter 2", "Chapter 3", "Chapter 4"]`

Your existing overlap grader then works unchanged, because it already compares each takeaway range against a single expected interval `[S, E]`.

For non-adjacent chapter sets, prefer an explicit list of allowed ranges and compute overlap against the union of intervals.

---

## 6) Main soft-chapter grader (single test)

### Test — Chapter Scope Soft Overlap Quality

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]

def grade(sample, item):
    """Return 1.0 when output matches schema/count and soft chapter-overlap thresholds."""
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
        S = int(item["expected_chapter_start"])
        E = int(item["expected_chapter_end"])
    except Exception:
        return 0.0

    if expected_n < 1 or S > E:
        return 0.0

    if len(takeaways) != expected_n:
        return 0.0

    strong_overlap = 0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0

        for k in REQUIRED_KEYS:
            if k not in t:
                return 0.0

        if not isinstance(t["approx_page_range"], str):
            return 0.0

        m = RANGE_RE.match(t["approx_page_range"])
        if not m:
            return 0.0

        A, B = int(m.group(1)), int(m.group(2))
        a, b = min(A, B), max(A, B)

        intersection = max(0, min(b, E) - max(a, S) + 1)
        range_len = b - a + 1
        overlap_ratio = intersection / range_len

        if overlap_ratio < 0.5:
            return 0.0

        if overlap_ratio >= 0.8:
            strong_overlap += 1

    return 1.0 if strong_overlap >= expected_n - 1 else 0.0
```

---

## 7) Split debug tests (small graders, float-only)

### Test 1 — JSON Parse Validity

```python
import json

def grade(sample, item):
    """Return 1.0 when output_text parses as JSON."""
    output_text = sample.get("output_text", "")
    try:
        json.loads(output_text)
        return 1.0
    except Exception:
        return 0.0
```

### Test 2 — Root Object and Takeaways Array

```python
import json

def grade(sample, item):
    """Return 1.0 when root object exists and takeaways is a list."""
    output_text = sample.get("output_text", "")
    try:
        obj = json.loads(output_text)
    except Exception:
        return 0.0

    if not isinstance(obj, dict):
        return 0.0
    if not isinstance(obj.get("takeaways"), list):
        return 0.0
    return 1.0
```

### Test 3 — Required Field Presence

```python
import json

REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]

def grade(sample, item):
    """Return 1.0 when all takeaways contain required fields."""
    output_text = sample.get("output_text", "")
    try:
        obj = json.loads(output_text)
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0
        for k in REQUIRED_KEYS:
            if k not in t:
                return 0.0

    return 1.0
```

### Test 4 — Expected Dataset Configuration

```python
def grade(sample, item):
    """Return 1.0 when expected count and chapter bounds are valid."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        s = int(item["expected_chapter_start"])
        e = int(item["expected_chapter_end"])
    except Exception:
        return 0.0

    if expected_n < 1:
        return 0.0
    if s > e:
        return 0.0
    return 1.0
```

### Test 5 — Exact Takeaway Count Match

```python
import json

def grade(sample, item):
    """Return 1.0 when takeaway count equals expected_takeaway_count."""
    output_text = sample.get("output_text", "")
    try:
        obj = json.loads(output_text)
        expected_n = int(item["expected_takeaway_count"])
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    return 1.0 if len(takeaways) == expected_n else 0.0
```

### Test 6 — Page Range Format Validation

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")

def grade(sample, item):
    """Return 1.0 when every approx_page_range matches p<start>-<end>."""
    output_text = sample.get("output_text", "")
    try:
        obj = json.loads(output_text)
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0
        rng = t.get("approx_page_range", "")
        if not isinstance(rng, str):
            return 0.0
        if not RANGE_RE.match(rng):
            return 0.0

    return 1.0
```

### Test 7 — Hard Floor Overlap (>= 0.5)

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")

def grade(sample, item):
    """Return 1.0 when no takeaway overlap ratio is below 0.5."""
    output_text = sample.get("output_text", "")
    try:
        obj = json.loads(output_text)
        s = int(item["expected_chapter_start"])
        e = int(item["expected_chapter_end"])
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    for t in takeaways:
        rng = t.get("approx_page_range", "") if isinstance(t, dict) else ""
        m = RANGE_RE.match(rng)
        if not m:
            return 0.0

        A, B = int(m.group(1)), int(m.group(2))
        a, b = min(A, B), max(A, B)
        intersection = max(0, min(b, e) - max(a, s) + 1)
        ratio = intersection / (b - a + 1)

        if ratio < 0.5:
            return 0.0

    return 1.0
```

### Test 8 — Soft Overlap Quality (>= 0.8 for N-1)

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")

def grade(sample, item):
    """Return 1.0 when at least N-1 takeaways have overlap ratio >= 0.8."""
    output_text = sample.get("output_text", "")
    try:
        obj = json.loads(output_text)
        s = int(item["expected_chapter_start"])
        e = int(item["expected_chapter_end"])
        expected_n = int(item["expected_takeaway_count"])
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    strong = 0
    for t in takeaways:
        rng = t.get("approx_page_range", "") if isinstance(t, dict) else ""
        m = RANGE_RE.match(rng)
        if not m:
            return 0.0

        A, B = int(m.group(1)), int(m.group(2))
        a, b = min(A, B), max(A, B)
        intersection = max(0, min(b, e) - max(a, s) + 1)
        ratio = intersection / (b - a + 1)

        if ratio >= 0.8:
            strong += 1

    return 1.0 if strong >= expected_n - 1 else 0.0
```

---

## 8) Recommended debug order

1. Test 1 — JSON Parse Validity
2. Test 2 — Root Object and Takeaways Array
3. Test 3 — Required Field Presence
4. Test 4 — Expected Dataset Configuration
5. Test 5 — Exact Takeaway Count Match
6. Test 6 — Page Range Format Validation
7. Test 7 — Hard Floor Overlap (>= 0.5)
8. Test 8 — Soft Overlap Quality (>= 0.8 for N-1)

This isolates format, schema, config, range, and overlap issues step by step.
---

## 9) Practical implementation notes (from prior review)

Strengths of this framework:
- Deterministic float-only contract (`1.0`/`0.0`) reduces integration ambiguity.
- Clear `sample` vs `item` separation helps isolate model-output vs dataset-config issues.
- The 8-step debug split is ordered to minimize time-to-root-cause.

Common edge cases to watch:
- Strict range regex (`^p([0-9]+)-([0-9]+)$`) rejects variants like `p40–42` or `p40 - 42`.
- Required-key checks validate presence, but not always semantic quality (empty strings/lists).
- For non-adjacent chapter scopes, use union-of-ranges overlap logic instead of single `[S, E]`.

Low-cost hardening options:
- Validate `id/title/claim` as non-empty strings.
- Validate `scope_keywords` as a non-empty list of strings.
- Keep production grader float-only, but optionally maintain a local debug helper that reports failure reasons.

