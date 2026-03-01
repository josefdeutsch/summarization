# Curator A.10 — Prompt Rewording Stability Grading Guide

## 1) Guide purpose
Use this guide to evaluate case A.10, where the instruction is slightly reworded but has the same meaning. The goal is to ensure output quality remains stable under minor phrasing changes: structure should stay consistent, clustering behavior should remain coherent, and takeaways should not collapse into trivial summaries.

This guide is optimized for debuggability by chunks:
- baseline chunk tests isolate parsing/schema issues,
- case-specific chunk tests isolate rewording-stability quality,
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
- Preserve conceptual rigor even when user wording is casual or slightly rephrased.

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
Could you pull out 8 solid takeaways from this book? Keep them practical and grounded in concrete ideas, not generic themes.
```

### Inline dataset row (.jsonl)
```jsonl
{"case_id":"A.10","input":"Could you pull out 8 solid takeaways from this book? Keep them practical and grounded in concrete ideas, not generic themes.","expected_takeaway_count":8,"max_takeaway_span_pages":40,"min_scope_keywords":3,"min_claim_char_len":90,"stability_anchor_terms":["feedback","constraint","trade-off","process","framework","mechanism"],"banned_generic_phrases":["is important","matters a lot","plays a key role"]}
```

## 3) Grader contract
- Signature must be `def grade(sample, item):`.
- Return float only: `1.0` pass, `0.0` fail.
- Parse model output from `sample.get("output_text", "")`.
- In this guide, every runnable snippet defines only `grade(sample, item)`.
- Case-specific naming is expressed in the test names.

## 4) Main grader (A10_rewording_stability_quality)
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def grade(sample, item):
    """Return 1.0 when baseline checks and A.10 rewording-stability checks pass."""
    output_text = sample.get("output_text", "")

    try:
        obj = json.loads(output_text)
        expected_n = int(item["expected_takeaway_count"])
        max_span = int(item.get("max_takeaway_span_pages", 40))
        min_scope_keywords = int(item.get("min_scope_keywords", 3))
        min_claim_char_len = int(item.get("min_claim_char_len", 90))
        anchors = item.get("stability_anchor_terms", [])
        banned = item.get("banned_generic_phrases", [])
    except Exception:
        return 0.0

    if isinstance(anchors, str):
        try:
            anchors = json.loads(anchors)
        except Exception:
            return 0.0
    if isinstance(banned, str):
        try:
            banned = json.loads(banned)
        except Exception:
            return 0.0

    if not isinstance(anchors, list) or not isinstance(banned, list):
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

        if not isinstance(claim, str) or len(claim.strip()) < min_claim_char_len:
            return 0.0
        if not isinstance(kws, list) or len(kws) < min_scope_keywords:
            return 0.0
        if not isinstance(rng, str):
            return 0.0

        m = RANGE_RE.match(rng)
        if not m:
            return 0.0

        a_raw, b_raw = int(m.group(1)), int(m.group(2))
        a, b = min(a_raw, b_raw), max(a_raw, b_raw)
        if (b - a + 1) > max_span:
            return 0.0

        cl = claim.lower()
        for phrase in banned:
            if isinstance(phrase, str) and phrase.strip() and phrase.lower() in cl:
                return 0.0

        anchor_ok = True
        if anchors:
            anchor_ok = False
            for term in anchors:
                if isinstance(term, str) and term.strip() and term.lower() in cl:
                    anchor_ok = True
                    break

        if anchor_ok:
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
    """Return 1.0 when A.10 dataset config fields are valid."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        max_span = int(item.get("max_takeaway_span_pages", 40))
        min_scope_keywords = int(item.get("min_scope_keywords", 3))
        min_claim_char_len = int(item.get("min_claim_char_len", 90))
        anchors = item.get("stability_anchor_terms", [])
        banned = item.get("banned_generic_phrases", [])
    except Exception:
        return 0.0

    if isinstance(anchors, str):
        try:
            anchors = json.loads(anchors)
        except Exception:
            return 0.0
    if isinstance(banned, str):
        try:
            banned = json.loads(banned)
        except Exception:
            return 0.0

    if expected_n < 1 or max_span < 1 or min_scope_keywords < 1 or min_claim_char_len < 20:
        return 0.0
    if not isinstance(anchors, list) or not isinstance(banned, list):
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

### Test 7 — A10_rewording_stability_non_triviality
```python
import json


def grade(sample, item):
    """Return 1.0 when at least N-1 claims remain non-trivial under reworded instruction."""
    try:
        obj = json.loads(sample.get("output_text", ""))
        expected_n = int(item["expected_takeaway_count"])
        anchors = item.get("stability_anchor_terms", [])
        banned = item.get("banned_generic_phrases", [])
    except Exception:
        return 0.0

    if isinstance(anchors, str):
        try:
            anchors = json.loads(anchors)
        except Exception:
            return 0.0
    if isinstance(banned, str):
        try:
            banned = json.loads(banned)
        except Exception:
            return 0.0

    if not isinstance(anchors, list) or not isinstance(banned, list):
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
        for phrase in banned:
            if isinstance(phrase, str) and phrase.strip() and phrase.lower() in cl:
                return 0.0

        anchor_ok = True
        if anchors:
            anchor_ok = False
            for term in anchors:
                if isinstance(term, str) and term.strip() and term.lower() in cl:
                    anchor_ok = True
                    break

        if anchor_ok:
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
7. Test 7 — A.10 rewording-stability non-triviality

## 7) Author checklist
- Keep this exact section order.
- Ensure every runnable snippet defines only `def grade(sample, item):`.
- Keep baseline tests generic.
- Name case-specific tests by use case (not generic labels).
- Add a docstring to every `grade` function.
- Keep tests minimal but sufficient for isolated debugging.
