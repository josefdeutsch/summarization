# Curator {{CASE_ID}} — {{CASE_TITLE}} Grading Guide Template

## 1) Guide purpose
Use this template to create a new float-only grader guide that matches the A.6/A.7 format and the OpenAI Evals Web UI execution model.

This template is optimized for **debuggability by chunks**:
- baseline chunk tests isolate parsing/schema issues,
- case-specific chunk tests isolate use-case logic,
- every code block is directly runnable as one grader.

## 2) Prompt package

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
```

### usermessage
```text
{{PLACEHOLDER_USERMESSAGE_FOR_CASE}}
```

### Inline dataset row (.jsonl)
```jsonl
{"case_id":"{{CASE_ID}}","input":"{{PLACEHOLDER_USERMESSAGE_FOR_CASE}}","expected_takeaway_count":8,"{{CASE_FIELD_1}}":"{{VALUE}}","{{CASE_FIELD_2}}":"{{VALUE}}"}
```

## 3) Grader contract
- Signature must be `def grade(sample, item):`.
- Return float only: `1.0` pass, `0.0` fail.
- Parse model output from `sample.get("output_text", "")`.
- In this template, every runnable snippet defines only `grade(sample, item)`.
- Express case-specific naming in section/test names (e.g., `{{CASE_ID}}_hard_floor`, `{{CASE_ID}}_soft_quality`).

## 4) Main grader ({{CASE_ID}}_main_quality)
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def grade(sample, item):
    """Return 1.0 when baseline checks and {{CASE_ID}}-specific quality checks pass."""
    output_text = sample.get("output_text", "")

    try:
        obj = json.loads(output_text)
        expected_n = int(item["expected_takeaway_count"])
    except Exception:
        return 0.0

    if not isinstance(obj, dict):
        return 0.0
    takeaways = obj.get("takeaways")
    if not isinstance(takeaways, list):
        return 0.0
    if len(takeaways) != expected_n:
        return 0.0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0
        for k in REQUIRED_KEYS:
            if k not in t:
                return 0.0

        rng = t.get("approx_page_range", "")
        if not isinstance(rng, str) or not RANGE_RE.match(rng):
            return 0.0

    # --- {{CASE_ID}}-specific logic starts here ---
    # Replace this placeholder with your use-case conditions.
    # Example:
    # threshold = int(item.get("{{CASE_THRESHOLD_FIELD}}", 1))
    # score = ...
    # if score < threshold:
    #     return 0.0
    # --- {{CASE_ID}}-specific logic ends here ---

    return 1.0
```

## 5) Split debug tests (chunk-by-chunk)
Run each test as a separate grader block in OpenAI Evals UI.

### Test 1 — Baseline JSON parse validity
```python
import json


def grade(sample, item):
    """Return 1.0 when output_text parses as JSON."""
    try:
        json.loads(sample.get("output_text", ""))
        return 1.0
    except Exception:
        return 0.0
```

### Test 2 — Baseline root object + takeaways array
```python
import json


def grade(sample, item):
    """Return 1.0 when root is object and `takeaways` is a list."""
    try:
        obj = json.loads(sample.get("output_text", ""))
    except Exception:
        return 0.0

    if not isinstance(obj, dict):
        return 0.0
    if not isinstance(obj.get("takeaways"), list):
        return 0.0
    return 1.0
```

### Test 3 — Baseline required takeaway fields
```python
import json

REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def grade(sample, item):
    """Return 1.0 when every takeaway includes all required keys."""
    try:
        obj = json.loads(sample.get("output_text", ""))
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

### Test 4 — Baseline dataset config validity
```python

def grade(sample, item):
    """Return 1.0 when dataset config fields required by this case are valid."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        # Add case fields here, e.g.:
        # hard_floor = int(item["{{CASE_FIELD_1}}"])
        # soft_floor = int(item["{{CASE_FIELD_2}}"])
    except Exception:
        return 0.0

    if expected_n < 1:
        return 0.0

    # Add additional case-specific config validation here.
    return 1.0
```

### Test 5 — Baseline exact takeaway count
```python
import json


def grade(sample, item):
    """Return 1.0 when takeaway count exactly matches expected_takeaway_count."""
    try:
        obj = json.loads(sample.get("output_text", ""))
        expected_n = int(item["expected_takeaway_count"])
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    return 1.0 if len(takeaways) == expected_n else 0.0
```

### Test 6 — Baseline page-range format validity
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")


def grade(sample, item):
    """Return 1.0 when every `approx_page_range` matches p<start>-<end>."""
    try:
        obj = json.loads(sample.get("output_text", ""))
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    for t in takeaways:
        rng = t.get("approx_page_range", "") if isinstance(t, dict) else ""
        if not isinstance(rng, str) or not RANGE_RE.match(rng):
            return 0.0

    return 1.0
```

### Test 7 — {{CASE_ID}}_usecase_specific_quality
```python
import json


def grade(sample, item):
    """Return 1.0 when {{CASE_ID}}-specific quality constraints pass."""
    try:
        obj = json.loads(sample.get("output_text", ""))
        expected_n = int(item["expected_takeaway_count"])
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list) or len(takeaways) != expected_n:
        return 0.0

    # Implement case-specific checks here.
    # Return 0.0 on fail, 1.0 on pass.
    return 1.0
```

## 6) Recommended debug order
1. Test 1 — JSON parse
2. Test 2 — root + takeaways list
3. Test 3 — required fields
4. Test 4 — dataset config
5. Test 5 — exact count
6. Test 6 — range format
7. Test 7 — case-specific quality

## 7) Author checklist
- Keep this exact section order.
- Ensure every runnable snippet defines only `def grade(sample, item):`.
- Keep baseline tests generic.
- Name case-specific tests by use case (not generic labels).
- Add a docstring to every `grade` function.
- Keep tests minimal but sufficient for isolated debugging.
