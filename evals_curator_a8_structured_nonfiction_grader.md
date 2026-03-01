# Curator A.8 — Structured Nonfiction Mechanism Extraction Grading Guide

## 1) Guide purpose
Use this guide to evaluate case A.8 for technical or structured nonfiction books. The goal is to verify that takeaways capture mechanisms, frameworks, and conceptual distinctions rather than vague high-level summaries.

This guide is optimized for debuggability by chunks:
- baseline chunk tests isolate parsing/schema issues,
- case-specific chunk tests isolate A.8 mechanism/framework quality,
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
- Prefer mechanism-rich claims over generic themes.

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
2) Takeaway count follows user requirements.
```

### usermessage
```text
I need 8 high-signal takeaways from this technical nonfiction book for a study guide. Focus on mechanisms, frameworks, and important conceptual distinctions rather than broad topic summaries.
```

### Inline dataset row (.jsonl)
```jsonl
{"case_id":"A.8","input":"I need 8 high-signal takeaways from this technical nonfiction book for a study guide. Focus on mechanisms, frameworks, and important conceptual distinctions rather than broad topic summaries.","expected_takeaway_count":8,"min_scope_keywords":3,"mechanism_terms":["framework","model","mechanism","process","trade-off","constraint","feedback","causal","condition"],"banned_vague_phrases":["is important","matters a lot","plays a key role"]}
```

## 3) Grader contract
- Signature must be `def grade(sample, item):`.
- Return float only: `1.0` pass, `0.0` fail.
- Parse model output from `sample.get("output_text", "")`.
- In this guide, every runnable snippet defines only `grade(sample, item)`.
- Case-specific naming is expressed in the test names.

## 4) Main grader (A8_mechanism_framework_quality)
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def grade(sample, item):
    """Return 1.0 when baseline checks and A.8 mechanism/framework checks pass."""
    output_text = sample.get("output_text", "")

    try:
        obj = json.loads(output_text)
        expected_n = int(item["expected_takeaway_count"])
        min_scope_keywords = int(item.get("min_scope_keywords", 3))
        mechanism_terms = item.get("mechanism_terms", [])
        banned_vague = item.get("banned_vague_phrases", [])
    except Exception:
        return 0.0

    if isinstance(mechanism_terms, str):
        try:
            mechanism_terms = json.loads(mechanism_terms)
        except Exception:
            return 0.0
    if isinstance(banned_vague, str):
        try:
            banned_vague = json.loads(banned_vague)
        except Exception:
            return 0.0

    if not isinstance(mechanism_terms, list) or not isinstance(banned_vague, list):
        return 0.0

    if not isinstance(obj, dict):
        return 0.0
    takeaways = obj.get("takeaways")
    if not isinstance(takeaways, list):
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

        claim = t.get("claim", "")
        kws = t.get("scope_keywords", [])
        rng = t.get("approx_page_range", "")
        title = t.get("title", "")

        if not isinstance(claim, str) or not claim.strip():
            return 0.0
        if not isinstance(title, str) or not title.strip():
            return 0.0
        if not isinstance(kws, list) or len(kws) < min_scope_keywords:
            return 0.0
        if not isinstance(rng, str) or not RANGE_RE.match(rng):
            return 0.0

        lowered = claim.lower()
        for phrase in banned_vague:
            if isinstance(phrase, str) and phrase.strip() and phrase.lower() in lowered:
                return 0.0

        mechanism_ok = True
        if mechanism_terms:
            mechanism_ok = False
            for term in mechanism_terms:
                if isinstance(term, str) and term.strip() and term.lower() in lowered:
                    mechanism_ok = True
                    break

        distinction_ok = any(x in lowered for x in ["vs", "versus", "compared to", "whereas", "trade-off", "if", "when"])

        if mechanism_ok or distinction_ok:
            strong += 1

    return 1.0 if strong >= expected_n - 1 else 0.0
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
import json


def grade(sample, item):
    """Return 1.0 when A.8 dataset config fields are valid."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        min_scope_keywords = int(item.get("min_scope_keywords", 3))
        mechanism_terms = item.get("mechanism_terms", [])
        banned_vague = item.get("banned_vague_phrases", [])
    except Exception:
        return 0.0

    if isinstance(mechanism_terms, str):
        try:
            mechanism_terms = json.loads(mechanism_terms)
        except Exception:
            return 0.0
    if isinstance(banned_vague, str):
        try:
            banned_vague = json.loads(banned_vague)
        except Exception:
            return 0.0

    if expected_n < 1 or min_scope_keywords < 1:
        return 0.0
    if not isinstance(mechanism_terms, list) or not isinstance(banned_vague, list):
        return 0.0
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

### Test 7 — A8_mechanism_framework_specificity
```python
import json


def grade(sample, item):
    """Return 1.0 when at least N-1 claims include mechanism/framework or conceptual distinction cues."""
    try:
        obj = json.loads(sample.get("output_text", ""))
        expected_n = int(item["expected_takeaway_count"])
        mechanism_terms = item.get("mechanism_terms", [])
    except Exception:
        return 0.0

    if isinstance(mechanism_terms, str):
        try:
            mechanism_terms = json.loads(mechanism_terms)
        except Exception:
            return 0.0

    if not isinstance(mechanism_terms, list):
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list) or len(takeaways) != expected_n:
        return 0.0

    strong = 0
    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0
        claim = t.get("claim", "")
        if not isinstance(claim, str):
            return 0.0

        cl = claim.lower()
        mechanism_ok = False
        for term in mechanism_terms:
            if isinstance(term, str) and term.strip() and term.lower() in cl:
                mechanism_ok = True
                break

        distinction_ok = any(x in cl for x in ["vs", "versus", "compared to", "whereas", "trade-off", "if", "when"])

        if mechanism_ok or distinction_ok:
            strong += 1

    return 1.0 if strong >= expected_n - 1 else 0.0
```

## 6) Recommended debug order
1. Test 1 — JSON parse
2. Test 2 — root + takeaways list
3. Test 3 — required fields
4. Test 4 — dataset config
5. Test 5 — exact count
6. Test 6 — range format
7. Test 7 — A.8 mechanism/framework specificity

## 7) Author checklist
- Keep this exact section order.
- Ensure every runnable snippet defines only `def grade(sample, item):`.
- Keep baseline tests generic.
- Name case-specific tests by use case (not generic labels).
- Add a docstring to every `grade` function.
- Keep tests minimal but sufficient for isolated debugging.
