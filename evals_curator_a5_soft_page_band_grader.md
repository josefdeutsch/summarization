# Curator A.5 — Soft Page-Band Scope Grading (Float-only Python Graders)

This guide mirrors the A.4 soft-chapter pattern, adapted for **A.5 page-band constraints**.

Contract:
- Python graders return **float only** (`1.0` PASS, `0.0` FAIL).
- Use `def grade(sample, item):`.
- Read model output from `sample.get("output_text", "")`.
- Parse JSON via `json.loads(output_text)`.

---

## 1) Python grader contract (critical)

- Return a float in `[0.0, 1.0]`.
- `1.0` means pass.
- `0.0` means fail.
- No dict return objects in this guide.

---

## 2) Runtime mapping: `sample` vs `item`

- `sample`: model output payload (`output_text`, `output_json`, `choices`, ...)
- `item`: dataset row (`expected_page_start`, `expected_page_end`, `expected_takeaway_count`, ...)

Typical access pattern:

```python
output_text = sample.get("output_text", "")
expected_n = int(item.get("expected_takeaway_count", 0))
```

---

## 3) Dataset fields for A.5 soft page-band checks

Use these row fields:
- `case_id`
- `input`
- `expected_scope_label`
- `expected_page_start`
- `expected_page_end`
- `expected_takeaway_count`

Example:

```json
{
  "case_id": "A.5",
  "input": "Extract exactly 8 information-rich takeaways from pages p80-p120.",
  "expected_scope_label": "Page band p80-p120",
  "expected_page_start": 80,
  "expected_page_end": 120,
  "expected_takeaway_count": 8
}
```

---

## 4) Soft-scope principle (ACTUAL vs EXPECTED)

- EXPECTED interval: `[S, E]` from dataset row.
- ACTUAL interval: parsed from `approx_page_range` (e.g., `p84-90`).
- Overlap per takeaway:
  - `intersection = max(0, min(b, E) - max(a, S) + 1)`
  - `range_len = b - a + 1`
  - `overlap_ratio = intersection / range_len`

Recommended rule:
- fail if any takeaway has `overlap_ratio < 0.5`
- pass if at least `expected_n - 1` takeaways have `overlap_ratio >= 0.8`

---

## 5) Main soft page-band grader (single test)

### Test — Page-Band Scope Soft Overlap Quality

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]

def grade(sample, item):
    """Return 1.0 when output matches schema/count and soft page-band overlap thresholds."""
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
        S = int(item["expected_page_start"])
        E = int(item["expected_page_end"])
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

        rng = t.get("approx_page_range")
        if not isinstance(rng, str):
            return 0.0

        m = RANGE_RE.match(rng)
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

## 6) Split debug tests (float-only)

### Test 1 — JSON Parse Validity

```python
import json

def grade(sample, item):
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
    try:
        expected_n = int(item["expected_takeaway_count"])
        s = int(item["expected_page_start"])
        e = int(item["expected_page_end"])
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
    output_text = sample.get("output_text", "")
    try:
        obj = json.loads(output_text)
        s = int(item["expected_page_start"])
        e = int(item["expected_page_end"])
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
    output_text = sample.get("output_text", "")
    try:
        obj = json.loads(output_text)
        s = int(item["expected_page_start"])
        e = int(item["expected_page_end"])
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

## 7) Recommended debug order

1. JSON Parse Validity
2. Root Object and Takeaways Array
3. Required Field Presence
4. Expected Dataset Configuration
5. Exact Takeaway Count Match
6. Page Range Format Validation
7. Hard Floor Overlap (>= 0.5)
8. Soft Overlap Quality (>= 0.8 for N-1)

This sequence isolates parse, schema, config, format, and overlap issues quickly.
