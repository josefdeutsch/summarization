# Curator A.1–A.3 — Baseline Structure & Clustering Width Grading (Float-only Python Graders)

This guide is built from the A.4/A.6 template style and tailored to your A.1–A.3 baseline runs.

## Chat prompt (Takeaway Curator)

Declare the following prompt as `systemmessage`:

### systemmessage
```text
You are Takeaway Curator.

Your responsibility is to extract structured, information-rich takeaways from a book using FileSearch.

Workflow requirements
- Use FileSearch to inspect the source before producing takeaways.
- If the user provides chapter/page scope, treat it as a hard boundary.
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

### usermessage (A.1)
```text
Use FileSearch on the uploaded book and identify 4–8 strong, information-rich takeaways.
```

### usermessage (A.2)
```text
Use FileSearch on the uploaded book and identify 4–8 strong, information-rich takeaways.
(Repeat-run stability check with same input.)
```

### usermessage (A.3)
```text
Identify the 4–8 most central, non-trivial takeaways from the entire book using FileSearch.
```


---

## 1) What this grader covers

A.1–A.3 here uses two deterministic checks per run:
1. **Schema Validator (always-on)** — output is valid JSON with required takeaway structure, including `approx_page_range`.
2. **Clustering Width Check** — each takeaway page span is limited (default max width: 40 pages).

These match your recorded labels:
- `prompt_1_A_Schema_Validator_*`
- `prompt_1_A_Clustering_Width_Check_*`

---

## 2) Expected dataset columns

Use these columns in each row (as provided):
- `case_id`
- `input`
- `notes`
- `scope_start_page`
- `scope_end_page`
- `prompt_1_input`
- `prompt_1_output`
- `prompt_1_A_Schema_Validator_label`
- `prompt_1_A_Schema_Validator_reasoning`
- `prompt_1_A_Schema_Validator_score`
- `prompt_1_A_Schema_Validator_pass`
- `prompt_1_A_Clustering_Width_Check_label`
- `prompt_1_A_Clustering_Width_Check_reasoning`
- `prompt_1_A_Clustering_Width_Check_score`
- `prompt_1_A_Clustering_Width_Check_pass`

Recommended runtime config fields for graders:
- `expected_min_takeaways` (default `4`)
- `expected_max_takeaways` (default `8`)
- `max_takeaway_width_pages` (default `40`)

---

## 3) Test A — Schema Validator (deterministic)

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def grade(sample, item):
    """Return 1.0 when output has valid JSON/schema and takeaway count in allowed bounds."""
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
        min_n = int(item.get("expected_min_takeaways", 4))
        max_n = int(item.get("expected_max_takeaways", 8))
    except Exception:
        return 0.0

    if min_n < 1 or max_n < min_n:
        return 0.0

    if not (min_n <= len(takeaways) <= max_n):
        return 0.0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0

        for k in REQUIRED_KEYS:
            if k not in t:
                return 0.0

        if not isinstance(t["scope_keywords"], list):
            return 0.0

        rng = t.get("approx_page_range")
        if not isinstance(rng, str) or not RANGE_RE.match(rng):
            return 0.0

    return 1.0
```

---

## 4) Test B — Clustering Width Check (semi-mechanical)

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")


def grade(sample, item):
    """Return 1.0 when each takeaway page-width is <= max_takeaway_width_pages."""
    output_text = sample.get("output_text", "")

    try:
        obj = json.loads(output_text)
        max_width = int(item.get("max_takeaway_width_pages", 40))
    except Exception:
        return 0.0

    if max_width < 1:
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
        width = b - a

        if width > max_width:
            return 0.0

    return 1.0
```

---

## 5) Optional scope-boundary add-on (if `scope_start_page/scope_end_page` are set)

If a row provides both `scope_start_page` and `scope_end_page`, add this test to enforce hard scope boundaries for all takeaway ranges.

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")


def grade(sample, item):
    try:
        obj = json.loads(sample.get("output_text", ""))
        s = int(item["scope_start_page"])
        e = int(item["scope_end_page"])
    except Exception:
        return 0.0

    if s > e:
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
        if a < s or b > e:
            return 0.0

    return 1.0
```

---

## 6) Recommended debug order (OpenAI Evals UI)

1. Schema Validator
2. Clustering Width Check
3. (Optional) Scope Boundary Check

This matches your A.1 infrastructure check, A.2 stability rerun, and A.3 baseline full-book clustering test loop.
