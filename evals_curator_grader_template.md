# Curator {{CASE_ID}} — {{CASE_TITLE}} Grading Guide Template

## 1) Guide purpose
Use this template to create a new **float-only Python grader guide** with the same structure as A.6 and A.7. Replace placeholders and keep the section order unchanged so every guide remains uniform and easy to review.

This template intentionally separates:
- **Baseline checks** (JSON parse + root `takeaways` shape).
- **Case-specific checks** (named for the use case).

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
- Return float only: `1.0` (pass) or `0.0` (fail).
- Parse model output from `sample.get("output_text", "")`.
- Keep baseline helper names unchanged across guides.
- Name non-baseline helpers after their case purpose.

## 4) Main grader template
```python
import json


def parse_output_json(sample):
    """Parse `sample.output_text` into a Python object; return None on parse failure."""
    try:
        return json.loads(sample.get("output_text", ""))
    except Exception:
        return None


def get_takeaways_array(obj):
    """Return `takeaways` when root schema is valid; otherwise return None."""
    if not isinstance(obj, dict):
        return None
    takeaways = obj.get("takeaways")
    return takeaways if isinstance(takeaways, list) else None


def validate_{{CASE_USECASE_NAME}}_constraints(takeaways, item):
    """Validate {{CASE_ID}}-specific requirements; return True/False."""
    # Implement case-specific checks here.
    # Example:
    # expected_n = int(item["expected_takeaway_count"])
    # return len(takeaways) == expected_n
    return True


def grade(sample, item):
    """Return 1.0 when baseline and case-specific checks pass; else 0.0."""
    obj = parse_output_json(sample)
    if obj is None:
        return 0.0

    takeaways = get_takeaways_array(obj)
    if takeaways is None:
        return 0.0

    return 1.0 if validate_{{CASE_USECASE_NAME}}_constraints(takeaways, item) else 0.0
```

## 5) Split debug tests (minimal set)
Run each test as a separate grader block in OpenAI Evals UI.

### Test 1 — Baseline JSON parse validity
```python
import json


def parse_output_json(sample):
    """Parse `sample.output_text` into a Python object; return None on parse failure."""
    try:
        return json.loads(sample.get("output_text", ""))
    except Exception:
        return None


def grade(sample, item):
    """Return 1.0 when output is valid JSON; else 0.0."""
    return 1.0 if parse_output_json(sample) is not None else 0.0
```

### Test 2 — Baseline takeaway container shape
```python
import json


def parse_output_json(sample):
    """Parse `sample.output_text` into a Python object; return None on parse failure."""
    try:
        return json.loads(sample.get("output_text", ""))
    except Exception:
        return None


def get_takeaways_array(obj):
    """Return `takeaways` when root schema is valid; otherwise return None."""
    if not isinstance(obj, dict):
        return None
    takeaways = obj.get("takeaways")
    return takeaways if isinstance(takeaways, list) else None


def grade(sample, item):
    """Return 1.0 when root object and takeaway array exist; else 0.0."""
    obj = parse_output_json(sample)
    if obj is None:
        return 0.0
    return 1.0 if get_takeaways_array(obj) is not None else 0.0
```

### Test 3 — Case-specific constraints
```python
import json


def parse_output_json(sample):
    """Parse `sample.output_text` into a Python object; return None on parse failure."""
    try:
        return json.loads(sample.get("output_text", ""))
    except Exception:
        return None


def validate_{{CASE_USECASE_NAME}}_constraints(takeaways, item):
    """Validate {{CASE_ID}}-specific requirements; return True/False."""
    # Implement case-specific checks here.
    return True


def grade(sample, item):
    """Return 1.0 when {{CASE_ID}}-specific checks pass; else 0.0."""
    obj = parse_output_json(sample)
    if not isinstance(obj, dict) or not isinstance(obj.get("takeaways"), list):
        return 0.0
    return 1.0 if validate_{{CASE_USECASE_NAME}}_constraints(obj["takeaways"], item) else 0.0
```

## 6) Recommended debug order
1. Test 1 (JSON parse)
2. Test 2 (root + `takeaways` list)
3. Test 3 (case-specific checks)

## 7) Author checklist
- Keep this exact section order.
- Keep baseline helper names: `parse_output_json`, `get_takeaways_array`.
- Use case-specific helper naming for non-baseline logic.
- Add docstrings to every function.
- Keep split debug tests minimal.
