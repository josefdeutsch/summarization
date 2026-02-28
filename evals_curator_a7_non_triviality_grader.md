# Curator A.7 — Non-triviality Filter Grading Guide

## 1) Guide purpose
This guide defines a **float-only Python grader** for case A.7. The objective is to block low-information, motivational filler and require takeaways that are concrete, scoped, and mechanism-aware. A pass therefore means: valid structure, correct takeaway count, and claims that avoid banned generic phrasing while remaining specific enough to be useful.

This guide follows the same structure as the other Curator guides:
1. Prompt package (system + user + inline dataset row).
2. Runtime contract (`sample`, `item`, float return only).
3. Main grader for final pass/fail.
4. Minimal split debug tests.

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

### usermessage (A.7)
```text
Extract exactly 8 information-rich takeaways from this mostly motivational/narrative book. Avoid platitudes and keep claims mechanism-rich and specific.
```

### Inline dataset row (.jsonl)
```jsonl
{"case_id":"A.7","input":"Extract exactly 8 information-rich takeaways from this mostly motivational/narrative book. Avoid platitudes and keep claims mechanism-rich and specific.","expected_takeaway_count":8,"min_claim_char_len":90,"min_scope_keywords":3,"banned_generic_phrases":["believe in yourself","never give up","stay positive"],"mechanism_terms":["feedback","loop","constraint","trade-off","cause","signal","pathway"]}
```

## 3) Grader contract
- Signature must be `def grade(sample, item):`.
- Return float only: `1.0` (pass) or `0.0` (fail).
- Parse model output from `sample.get("output_text", "")`.
- `item` contains thresholds and banned/mechanism term lists.

## 4) Main grader (A.7 non-triviality)
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


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


def has_range_format(range_text):
    """Return True when range uses exact `p<start>-<end>` formatting."""
    return isinstance(range_text, str) and RANGE_RE.match(range_text) is not None


def contains_any_term(text, terms):
    """Return True when any non-empty term appears in text (case-insensitive)."""
    if not isinstance(text, str):
        return False
    lowered = text.lower()
    for term in terms:
        if isinstance(term, str) and term.strip() and term.lower() in lowered:
            return True
    return False


def validate_non_triviality_constraints(takeaways, item):
    """Validate A.7-specific quality constraints for claim richness and mechanism grounding."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        min_claim_chars = int(item.get("min_claim_char_len", 90))
        min_scope_keywords = int(item.get("min_scope_keywords", 3))
    except Exception:
        return False

    banned_phrases = item.get("banned_generic_phrases", [])
    mechanism_terms = item.get("mechanism_terms", [])
    if not isinstance(banned_phrases, list) or not isinstance(mechanism_terms, list):
        return False

    if len(takeaways) != expected_n:
        return False

    strong_takeaways = 0
    for takeaway in takeaways:
        if not isinstance(takeaway, dict):
            return False
        for key in REQUIRED_KEYS:
            if key not in takeaway:
                return False

        claim = takeaway.get("claim", "")
        keywords = takeaway.get("scope_keywords", [])
        page_range = takeaway.get("approx_page_range", "")

        if not isinstance(claim, str) or len(claim.strip()) < min_claim_chars:
            return False
        if not isinstance(keywords, list):
            return False
        if not has_range_format(page_range):
            return False

        for phrase in banned_phrases:
            if isinstance(phrase, str) and phrase.strip() and phrase.lower() in claim.lower():
                return False

        mechanism_ok = True if not mechanism_terms else contains_any_term(claim, mechanism_terms)
        if len(keywords) >= min_scope_keywords and mechanism_ok:
            strong_takeaways += 1

    return strong_takeaways >= expected_n - 1


def grade(sample, item):
    """Return 1.0 when baseline schema checks and A.7 non-triviality checks pass."""
    obj = parse_output_json(sample)
    if obj is None:
        return 0.0

    takeaways = get_takeaways_array(obj)
    if takeaways is None:
        return 0.0

    return 1.0 if validate_non_triviality_constraints(takeaways, item) else 0.0
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

### Test 3 — A.7 non-triviality constraints
```python
import json


def parse_output_json(sample):
    """Parse `sample.output_text` into a Python object; return None on parse failure."""
    try:
        return json.loads(sample.get("output_text", ""))
    except Exception:
        return None


def contains_any_term(text, terms):
    """Return True when any non-empty term appears in text (case-insensitive)."""
    if not isinstance(text, str):
        return False
    lowered = text.lower()
    for term in terms:
        if isinstance(term, str) and term.strip() and term.lower() in lowered:
            return True
    return False


def validate_non_triviality_constraints(takeaways, item):
    """Validate count, claim length, banned phrase filter, and mechanism softness for A.7."""
    expected_n = int(item["expected_takeaway_count"])
    min_claim_chars = int(item.get("min_claim_char_len", 90))
    min_scope_keywords = int(item.get("min_scope_keywords", 3))
    banned_phrases = item.get("banned_generic_phrases", [])
    mechanism_terms = item.get("mechanism_terms", [])

    if len(takeaways) != expected_n:
        return False

    strong = 0
    for t in takeaways:
        claim = t.get("claim", "") if isinstance(t, dict) else ""
        keywords = t.get("scope_keywords", []) if isinstance(t, dict) else []
        if not isinstance(claim, str) or len(claim.strip()) < min_claim_chars:
            return False
        for phrase in banned_phrases:
            if isinstance(phrase, str) and phrase.strip() and phrase.lower() in claim.lower():
                return False
        mechanism_ok = True if not mechanism_terms else contains_any_term(claim, mechanism_terms)
        if isinstance(keywords, list) and len(keywords) >= min_scope_keywords and mechanism_ok:
            strong += 1

    return strong >= expected_n - 1


def grade(sample, item):
    """Return 1.0 when A.7-specific non-triviality checks pass; else 0.0."""
    obj = parse_output_json(sample)
    if not isinstance(obj, dict) or not isinstance(obj.get("takeaways"), list):
        return 0.0
    return 1.0 if validate_non_triviality_constraints(obj["takeaways"], item) else 0.0
```

## 6) Recommended debug order
1. Test 1 (JSON parse)
2. Test 2 (root + `takeaways` list)
3. Test 3 (A.7 non-triviality)
