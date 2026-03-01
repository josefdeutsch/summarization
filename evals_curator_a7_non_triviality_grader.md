# Curator A.7 — Non-triviality Filter Grading Guide

## 1) Guide purpose
This guide defines a float-only grader for case A.7. It checks whether the model avoids motivational filler and returns **specific, mechanism-aware takeaways**. The intent is to reject outputs that are technically valid JSON but semantically generic.

A.7 passes only when output satisfies:
- baseline JSON/schema checks,
- exact takeaway count,
- valid page-range format,
- hard non-triviality floor (claim length + banned phrase filter),
- and soft mechanism richness for most takeaways (`N-1` rule).

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
- Prefer mechanism-rich claims over inspirational principles.

Page citation requirements (critical)
- Each takeaway must include `approx_page_range`.
- Each takeaway must use exactly one contiguous page range.
- A takeaway may use a broader single contiguous range when the underlying argument unfolds across several pages (for example, around 6–15 pages when needed).
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

### usermessage (A.7)
```text
I'm preparing a workshop and need 8 practical takeaways from this book that people can apply. Focus on concrete mechanisms and avoid generic motivational advice.
```

### Inline dataset row (.jsonl)
```jsonl
{"case_id":"A.7","input":"I'm preparing a workshop and need 8 practical takeaways from this book that people can apply. Focus on concrete mechanisms and avoid generic motivational advice.","expected_takeaway_count":8,"min_claim_char_len":90,"min_scope_keywords":3,"banned_generic_phrases":["believe in yourself","never give up","stay positive"],"mechanism_terms":["feedback","loop","constraint","trade-off","cause","signal","pathway"]}
```

## 3) Grader contract
- Signature must be `def grade(sample, item):`.
- Return float only: `1.0` pass, `0.0` fail.
- Parse output from `sample.get("output_text", "")`.
- Keep baseline checks generic and case checks use-case specific.

## 4) Main grader (A7_non_triviality_quality)
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def grade(sample, item):
    """Return 1.0 when baseline schema checks and A.7 non-triviality checks pass."""
    output_text = sample.get("output_text", "")

    try:
        obj = json.loads(output_text)
        expected_n = int(item["expected_takeaway_count"])
        min_claim_chars = int(item.get("min_claim_char_len", 90))
        min_scope_keywords = int(item.get("min_scope_keywords", 3))
    except Exception:
        return 0.0

    if not isinstance(obj, dict):
        return 0.0
    takeaways = obj.get("takeaways")
    if not isinstance(takeaways, list):
        return 0.0
    if len(takeaways) != expected_n:
        return 0.0

    banned_phrases = item.get("banned_generic_phrases", [])
    mechanism_terms = item.get("mechanism_terms", [])

    # OpenAI Evals rows sometimes arrive with list-like fields serialized as JSON strings.
    if isinstance(banned_phrases, str):
        try:
            banned_phrases = json.loads(banned_phrases)
        except Exception:
            return 0.0
    if isinstance(mechanism_terms, str):
        try:
            mechanism_terms = json.loads(mechanism_terms)
        except Exception:
            return 0.0

    if not isinstance(banned_phrases, list) or not isinstance(mechanism_terms, list):
        return 0.0

    strong_takeaways = 0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0
        for k in REQUIRED_KEYS:
            if k not in t:
                return 0.0

        claim = t.get("claim", "")
        keywords = t.get("scope_keywords", [])
        rng = t.get("approx_page_range", "")

        if not isinstance(claim, str) or len(claim.strip()) < min_claim_chars:
            return 0.0
        if not isinstance(keywords, list):
            return 0.0
        if not isinstance(rng, str) or not RANGE_RE.match(rng):
            return 0.0

        claim_lower = claim.lower()
        for phrase in banned_phrases:
            if isinstance(phrase, str) and phrase.strip() and phrase.lower() in claim_lower:
                return 0.0

        mechanism_ok = True
        if mechanism_terms:
            mechanism_ok = False
            for term in mechanism_terms:
                if isinstance(term, str) and term.strip() and term.lower() in claim_lower:
                    mechanism_ok = True
                    break

        if len(keywords) >= min_scope_keywords and mechanism_ok:
            strong_takeaways += 1

    return 1.0 if strong_takeaways >= expected_n - 1 else 0.0
```

## 5) Split debug tests (manageable chunks)
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
    """Return 1.0 when A.7 threshold/list config in dataset row is valid."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        min_claim_chars = int(item.get("min_claim_char_len", 90))
        min_scope_keywords = int(item.get("min_scope_keywords", 3))
        banned = item.get("banned_generic_phrases", [])
        mech = item.get("mechanism_terms", [])
    except Exception:
        return 0.0

    # Accept either native lists or JSON-stringified lists.
    if isinstance(banned, str):
        try:
            banned = json.loads(banned)
        except Exception:
            return 0.0
    if isinstance(mech, str):
        try:
            mech = json.loads(mech)
        except Exception:
            return 0.0

    if expected_n < 1 or min_claim_chars < 20 or min_scope_keywords < 1:
        return 0.0
    if not isinstance(banned, list) or not isinstance(mech, list):
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

### Test 6 — A7_hard_non_triviality_floor
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")


def grade(sample, item):
    """Return 1.0 when claims meet hard floor: length, no banned phrase, valid range format."""
    try:
        obj = json.loads(sample.get("output_text", ""))
        min_claim_chars = int(item.get("min_claim_char_len", 90))
        banned = item.get("banned_generic_phrases", [])
    except Exception:
        return 0.0

    if isinstance(banned, str):
        try:
            banned = json.loads(banned)
        except Exception:
            return 0.0

    if not isinstance(banned, list):
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0
        claim = t.get("claim", "")
        rng = t.get("approx_page_range", "")

        if not isinstance(claim, str) or len(claim.strip()) < min_claim_chars:
            return 0.0
        if not isinstance(rng, str) or not RANGE_RE.match(rng):
            return 0.0

        cl = claim.lower()
        for phrase in banned:
            if isinstance(phrase, str) and phrase.strip() and phrase.lower() in cl:
                return 0.0

    return 1.0
```

### Test 7 — A7_soft_mechanism_specificity
```python
import json


def grade(sample, item):
    """Return 1.0 when at least N-1 takeaways are keyword-rich and mechanism-grounded."""
    try:
        obj = json.loads(sample.get("output_text", ""))
        expected_n = int(item["expected_takeaway_count"])
        min_scope_keywords = int(item.get("min_scope_keywords", 3))
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
        keywords = t.get("scope_keywords", [])
        if not isinstance(claim, str) or not isinstance(keywords, list):
            return 0.0

        mechanism_ok = True
        if mechanism_terms:
            mechanism_ok = False
            cl = claim.lower()
            for term in mechanism_terms:
                if isinstance(term, str) and term.strip() and term.lower() in cl:
                    mechanism_ok = True
                    break

        if len(keywords) >= min_scope_keywords and mechanism_ok:
            strong += 1

    return 1.0 if strong >= expected_n - 1 else 0.0
```

## 6) Recommended debug order
1. Test 1 — JSON parse
2. Test 2 — root + takeaways list
3. Test 3 — required fields
4. Test 4 — dataset config
5. Test 5 — exact count
6. Test 6 — hard non-triviality floor
7. Test 7 — soft mechanism specificity
