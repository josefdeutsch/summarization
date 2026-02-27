# Curator A.7 — Non-triviality Filter Grading (Float-only Python Graders)

This guide follows the same Curator grader structure and targets A.7: filtering out platitudes in motivational/narrative books.

## What this test framework does (brief)

This framework checks that takeaways remain structured and information-rich instead of generic advice.

**Goal:** reject shallow/platitude outputs and reward mechanism-oriented, specific claims.

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

### usermessage (A.7 — non-triviality filter)
```text
Extract exactly 8 information-rich takeaways from this mostly motivational/narrative book. Avoid platitudes and keep claims mechanism-rich and specific.
```

---

## 1) Python grader contract (critical)

- Return float only: `1.0` PASS, `0.0` FAIL.
- Use `def grade(sample, item):`.
- Parse output from `sample.get("output_text", "")` with `json.loads`.
- Do not return dicts.

---

## 2) Runtime mapping: `sample` vs `item`

- `sample`: model output payload.
- `item`: dataset row config.

Typical fields for A.7 rows:
- `case_id`
- `input`
- `expected_takeaway_count`
- `min_claim_char_len` (recommended `90`)
- `min_scope_keywords` (recommended `3`)
- `banned_generic_phrases` (optional list)
- `mechanism_terms` (optional list)

Example row:

```json
{
  "case_id": "A.7",
  "input": "Extract exactly 8 information-rich takeaways from this mostly motivational/narrative book. Avoid platitudes and keep claims mechanism-rich and specific.",
  "expected_takeaway_count": 8,
  "min_claim_char_len": 90,
  "min_scope_keywords": 3,
  "banned_generic_phrases": ["believe in yourself", "never give up", "stay positive"],
  "mechanism_terms": ["feedback", "loop", "constraint", "trade-off", "cause", "signal", "pathway"]
}
```

---

## 3) Case logic (ACTUAL vs EXPECTED)

- Hard fail if any takeaway claim is too short or contains banned generic phrasing.
- Strong takeaway criteria:
  - claim length >= `min_claim_char_len`
  - `scope_keywords` count >= `min_scope_keywords`
  - claim contains at least one mechanism term (if list provided)
- Pass when at least `expected_n - 1` takeaways are strong.

---

## 4) Main grader — Non-triviality Quality

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def has_any_term(text, terms):
    t = text.lower()
    for term in terms:
        if isinstance(term, str) and term.strip() and term.lower() in t:
            return True
    return False


def grade(sample, item):
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
        min_claim_len = int(item.get("min_claim_char_len", 90))
        min_kw = int(item.get("min_scope_keywords", 3))
    except Exception:
        return 0.0

    banned = item.get("banned_generic_phrases", [])
    mech_terms = item.get("mechanism_terms", [])

    if not isinstance(banned, list) or not isinstance(mech_terms, list):
        return 0.0

    if expected_n < 1 or min_claim_len < 20 or min_kw < 1:
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

        claim = t.get("claim")
        kws = t.get("scope_keywords")
        rng = t.get("approx_page_range")

        if not isinstance(claim, str) or not isinstance(kws, list) or not isinstance(rng, str):
            return 0.0

        if not RANGE_RE.match(rng):
            return 0.0

        claim_l = claim.lower()

        # hard fail: obvious platitude phrase present
        for phrase in banned:
            if isinstance(phrase, str) and phrase.strip() and phrase.lower() in claim_l:
                return 0.0

        # hard fail: too short claim
        if len(claim.strip()) < min_claim_len:
            return 0.0

        mechanism_ok = True if not mech_terms else has_any_term(claim, mech_terms)

        if len(kws) >= min_kw and mechanism_ok:
            strong += 1

    return 1.0 if strong >= expected_n - 1 else 0.0
```

---

## 5) Split debug tests (float-only)

### Test 1 — JSON Parse Validity
- `json.loads(sample["output_text"])` must succeed.

### Test 2 — Root Object + Takeaways Array
- Root must be dict with `takeaways` list.

### Test 3 — Required Field Presence
- Every takeaway must include `id`, `title`, `claim`, `scope_keywords`, `approx_page_range`.

### Test 4 — Dataset Config Validity
- Validate `expected_takeaway_count`, `min_claim_char_len`, `min_scope_keywords`.

### Test 5 — Exact Takeaway Count Match
- Require `len(takeaways) == expected_takeaway_count`.

### Test 6 — Range Format Validation
- Require `approx_page_range` to match `^p([0-9]+)-([0-9]+)$`.

### Test 7 — Hard Non-triviality Floor
- Fail if claim is too short or contains banned generic phrase.

### Test 8 — Soft Mechanism Quality
- Require at least `N-1` takeaways with keyword richness + mechanism term grounding.

---

## 6) Recommended debug order

1. Test 1 — JSON Parse
2. Test 2 — Root + list
3. Test 3 — Required fields
4. Test 4 — Dataset config
5. Test 5 — Count match
6. Test 6 — Range format
7. Test 7 — Hard non-triviality floor
8. Test 8 — Soft mechanism quality
