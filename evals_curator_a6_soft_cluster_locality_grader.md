# Curator A.6 — Soft Cluster-Locality Grading Guide

## 1) Guide purpose
This guide defines a float-only grader for case A.6. It checks whether takeaway extraction stays **locally coherent**: each takeaway must be schema-valid, use one valid contiguous page range, and remain narrow enough to avoid blending distant parts of the book into one claim.

A.6 focuses on retrieval discipline rather than prose quality. A pass means:
- valid JSON output with required takeaway fields,
- expected takeaway count,
- valid page-range formatting,
- per-takeaway locality (`span <= max_takeaway_span_pages`),
- and soft cluster anchoring for most takeaways (`N-1` rule).

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

### usermessage (A.6)
```text
Extract exactly 8 information-rich takeaways from the book. Keep each takeaway locally coherent and avoid mixing distant sections.
```

### Inline dataset row (.jsonl)
```jsonl
{"case_id":"A.6","input":"Extract exactly 8 information-rich takeaways from the book. Keep each takeaway locally coherent and avoid mixing distant sections.","expected_takeaway_count":8,"max_takeaway_span_pages":6,"required_cluster_ranges":[[38,66],[100,134],[180,210]]}
```

## 3) Grader contract
- Signature must be `def grade(sample, item):`.
- Return float only: `1.0` pass, `0.0` fail.
- Parse model output from `sample.get("output_text", "")`.
- `item` carries runtime thresholds and cluster zones.

## 4) Main grader (A6_cluster_locality)
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")
REQUIRED_KEYS = ["id", "title", "claim", "scope_keywords", "approx_page_range"]


def grade(sample, item):
    """Return 1.0 when baseline schema checks and A.6 locality/cluster checks pass."""
    output_text = sample.get("output_text", "")

    try:
        obj = json.loads(output_text)
        expected_n = int(item["expected_takeaway_count"])
        max_span = int(item["max_takeaway_span_pages"])
    except Exception:
        return 0.0

    if not isinstance(obj, dict):
        return 0.0
    takeaways = obj.get("takeaways")
    if not isinstance(takeaways, list):
        return 0.0

    cluster_ranges = item.get("required_cluster_ranges", [])
    if not isinstance(cluster_ranges, list):
        return 0.0

    normalized_clusters = []
    for zone in cluster_ranges:
        if not (isinstance(zone, list) and len(zone) == 2):
            return 0.0
        try:
            z1, z2 = int(zone[0]), int(zone[1])
        except Exception:
            return 0.0
        normalized_clusters.append((min(z1, z2), max(z1, z2)))

    if expected_n < 1 or max_span < 1:
        return 0.0
    if len(takeaways) != expected_n:
        return 0.0

    strong_anchors = 0

    for t in takeaways:
        if not isinstance(t, dict):
            return 0.0
        for k in REQUIRED_KEYS:
            if k not in t:
                return 0.0

        rng = t.get("approx_page_range", "")
        if not isinstance(rng, str):
            return 0.0

        m = RANGE_RE.match(rng)
        if not m:
            return 0.0

        a_raw, b_raw = int(m.group(1)), int(m.group(2))
        a, b = min(a_raw, b_raw), max(a_raw, b_raw)
        span = b - a + 1
        if span > max_span:
            return 0.0

        if normalized_clusters:
            best_ratio = 0.0
            for s, e in normalized_clusters:
                inter = max(0, min(b, e) - max(a, s) + 1)
                ratio = inter / span
                if ratio > best_ratio:
                    best_ratio = ratio
            if best_ratio >= 0.80:
                strong_anchors += 1

    if normalized_clusters:
        return 1.0 if strong_anchors >= expected_n - 1 else 0.0

    return 1.0
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

def grade(sample, item):
    """Return 1.0 when expected_n, max_span, and cluster config are valid."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        max_span = int(item["max_takeaway_span_pages"])
        clusters = item.get("required_cluster_ranges", [])
    except Exception:
        return 0.0

    if expected_n < 1 or max_span < 1:
        return 0.0
    if not isinstance(clusters, list):
        return 0.0

    for c in clusters:
        if not (isinstance(c, list) and len(c) == 2):
            return 0.0
        try:
            int(c[0]); int(c[1])
        except Exception:
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

### Test 7 — A6_cluster_locality_span_and_anchor
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")


def grade(sample, item):
    """Return 1.0 when each span is local and at least N-1 takeaways strongly anchor to cluster zones."""
    try:
        obj = json.loads(sample.get("output_text", ""))
        expected_n = int(item["expected_takeaway_count"])
        max_span = int(item["max_takeaway_span_pages"])
        clusters = item.get("required_cluster_ranges", [])
    except Exception:
        return 0.0

    takeaways = obj.get("takeaways") if isinstance(obj, dict) else None
    if not isinstance(takeaways, list) or len(takeaways) != expected_n:
        return 0.0
    if not isinstance(clusters, list):
        return 0.0

    normalized = []
    for c in clusters:
        if not (isinstance(c, list) and len(c) == 2):
            return 0.0
        try:
            s, e = int(c[0]), int(c[1])
        except Exception:
            return 0.0
        normalized.append((min(s, e), max(s, e)))

    anchored = 0
    for t in takeaways:
        rng = t.get("approx_page_range", "") if isinstance(t, dict) else ""
        m = RANGE_RE.match(rng) if isinstance(rng, str) else None
        if not m:
            return 0.0

        a_raw, b_raw = int(m.group(1)), int(m.group(2))
        a, b = min(a_raw, b_raw), max(a_raw, b_raw)
        span = b - a + 1
        if span > max_span:
            return 0.0

        if normalized:
            best = 0.0
            for s, e in normalized:
                inter = max(0, min(b, e) - max(a, s) + 1)
                best = max(best, inter / span)
            if best >= 0.80:
                anchored += 1

    if normalized:
        return 1.0 if anchored >= expected_n - 1 else 0.0
    return 1.0
```

## 6) Recommended debug order
1. Test 1 — JSON parse
2. Test 2 — root + takeaways list
3. Test 3 — required fields
4. Test 4 — dataset config
5. Test 5 — exact count
6. Test 6 — range format
7. Test 7 — A6 locality span + anchoring
