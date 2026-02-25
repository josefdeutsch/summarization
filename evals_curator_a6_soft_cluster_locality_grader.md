# Curator A.6 — Soft Cluster-Locality Grading (Float-only Python Graders)

This section mirrors the A.4 float-only style, adapted for A.6.

## Chat prompt (Takeaway Curator)

Declare the following prompt as `systemmessage`:

### systemmessage
```text
You are Takeaway Curator.

Your responsibility is to extract structured, information-rich takeaways from a book using FileSearch.

Core behavior
- Follow the requested chapter scope exactly (e.g., "Chapter 2").
- Do not require a numeric page interval from the user.
- Prefer depth within a concept and keep each takeaway locally coherent.
- Each takeaway must map to exactly one contiguous page span.

Quality rules
- Select central, non-trivial insights.
- Avoid generic advice, repetition, and padding.
- Avoid phrasing like "the author says".

Range rules
- approx_page_range must be formatted exactly as: p<start>-<end>
- Example valid: p82-85
- Example invalid: p82-p85, 82-85, p82–85, p82 - 85

Output contract (strict)
- Output JSON only (no markdown, no prose).
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
1) All takeaways belong to the requested chapter.
2) Every takeaway has exactly one contiguous approx_page_range.
3) Range format is p<start>-<end>.
4) JSON is valid and schema-complete.
```

### usermessage
```text
Extract exactly 8 information-rich takeaways from the book. Keep each takeaway locally coherent and avoid mixing distant sections.
```

---

### What A.6 is trying to prevent
- A single takeaway that merges content from distant parts of the book.
- “Global summary” style claims that are not anchored to one local evidence region.
- Loose range formatting that breaks deterministic checking.

### Python grader contract (critical)
- Return float only: `1.0` pass, `0.0` fail.
- Function signature: `def grade(sample, item):`
- Parse model output from `sample.get("output_text", "")`.
- Use strict JSON parse: `json.loads(output_text)`.

### Runtime mapping
- `sample` = model output payload.
- `item` = dataset row config for expected eval conditions.

Typical fields for A.6 rows:
- `case_id`
- `input`
- `expected_takeaway_count`
- `max_takeaway_span_pages` (e.g., `6`)
- `required_cluster_ranges` (list of expected conceptual zones, optional but recommended)

Example dataset row:

```json
{
  "case_id": "A.6",
  "input": "Extract exactly 8 information-rich takeaways from the book. Keep each takeaway locally coherent and avoid mixing distant sections.",
  "expected_takeaway_count": 8,
  "max_takeaway_span_pages": 6,
  "required_cluster_ranges": [[38, 66], [100, 134], [180, 210]]
}
```

---

## 1) Main grader — Soft Cluster Locality Quality

```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def overlaps(a, b, c, d):
    return max(0, min(b, d) - max(a, c) + 1)


def grade(sample, item):
    """Return 1.0 when schema/count pass and takeaway ranges are local + cluster-anchored."""
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
        max_span = int(item["max_takeaway_span_pages"])
    except Exception:
        return 0.0

    cluster_ranges = item.get("required_cluster_ranges", [])
    if not isinstance(cluster_ranges, list):
        return 0.0

    normalized_clusters = []
    for r in cluster_ranges:
        if not (isinstance(r, list) and len(r) == 2):
            return 0.0
        try:
            s, e = int(r[0]), int(r[1])
        except Exception:
            return 0.0
        if s > e:
            return 0.0
        normalized_clusters.append((s, e))

    if expected_n < 1 or max_span < 1:
        return 0.0

    if len(takeaways) != expected_n:
        return 0.0

    anchored_count = 0

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
        span = b - a + 1

        # hard locality floor: each takeaway must remain narrow/local
        if span > max_span:
            return 0.0

        # optional soft requirement: ranges should anchor to declared cluster regions
        if normalized_clusters:
            best_overlap_ratio = 0.0
            for s, e in normalized_clusters:
                inter = overlaps(a, b, s, e)
                ratio = inter / span
                if ratio > best_overlap_ratio:
                    best_overlap_ratio = ratio

            # fail if this takeaway is mostly outside all declared clusters
            if best_overlap_ratio < 0.5:
                return 0.0
            if best_overlap_ratio >= 0.8:
                anchored_count += 1

    if not normalized_clusters:
        return 1.0

    # at least N-1 takeaways should be strongly anchored to known cluster zones
    return 1.0 if anchored_count >= expected_n - 1 else 0.0
```

---

## 2) Split debug tests (float-only)

Use these in OpenAI Evals Web UI as separate grader experiments to isolate failures.

### Test 1 — JSON parse validity
```python
import json

def grade(sample, item):
    try:
        json.loads(sample.get("output_text", ""))
        return 1.0
    except Exception:
        return 0.0
```

### Test 2 — Root object + takeaways list
```python
import json

def grade(sample, item):
    try:
        obj = json.loads(sample.get("output_text", ""))
    except Exception:
        return 0.0
    return 1.0 if isinstance(obj, dict) and isinstance(obj.get("takeaways"), list) else 0.0
```

### Test 3 — Required key presence
```python
import json

REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]

def grade(sample, item):
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

### Test 4 — Expected dataset config validity
```python
def grade(sample, item):
    try:
        expected_n = int(item["expected_takeaway_count"])
        max_span = int(item["max_takeaway_span_pages"])
    except Exception:
        return 0.0
    if expected_n < 1 or max_span < 1:
        return 0.0
    return 1.0
```

### Test 5 — Exact takeaway count
```python
import json

def grade(sample, item):
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

### Test 6 — Page range format validity
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")

def grade(sample, item):
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

### Test 7 — Hard locality floor (`span <= max_takeaway_span_pages`)
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")

def grade(sample, item):
    try:
        obj = json.loads(sample.get("output_text", ""))
        max_span = int(item["max_takeaway_span_pages"])
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
        if (b - a + 1) > max_span:
            return 0.0
    return 1.0
```

### Test 8 — Soft cluster anchoring quality (`>= 0.8` for `N-1`)
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")

def overlap(a, b, c, d):
    return max(0, min(b, d) - max(a, c) + 1)


def grade(sample, item):
    try:
        obj = json.loads(sample.get("output_text", ""))
        expected_n = int(item["expected_takeaway_count"])
        clusters = item.get("required_cluster_ranges", [])
    except Exception:
        return 0.0

    if not isinstance(clusters, list):
        return 0.0

    normalized = []
    for r in clusters:
        if not (isinstance(r, list) and len(r) == 2):
            return 0.0
        try:
            s, e = int(r[0]), int(r[1])
        except Exception:
            return 0.0
        if s > e:
            return 0.0
        normalized.append((s, e))

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list):
        return 0.0

    if not normalized:
        return 1.0

    strong = 0
    for t in takeaways:
        rng = t.get("approx_page_range", "") if isinstance(t, dict) else ""
        m = RANGE_RE.match(rng)
        if not m:
            return 0.0
        A, B = int(m.group(1)), int(m.group(2))
        a, b = min(A, B), max(A, B)
        span = b - a + 1

        best = 0.0
        for s, e in normalized:
            inter = overlap(a, b, s, e)
            ratio = inter / span
            if ratio > best:
                best = ratio

        if best >= 0.8:
            strong += 1

    return 1.0 if strong >= expected_n - 1 else 0.0
```

---

## 3) Recommended debug order in OpenAI Evals Web UI
1. Test 1 — JSON Parse
2. Test 2 — Root + list
3. Test 3 — Required fields
4. Test 4 — Dataset config
5. Test 5 — Count match
6. Test 6 — Range format
7. Test 7 — Hard locality floor
8. Test 8 — Soft cluster anchoring

This order isolates syntax, schema, dataset setup, and locality/cluster logic progressively.
