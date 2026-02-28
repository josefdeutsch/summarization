# Curator A.6 — Soft Cluster-Locality Grading Guide

## 1) Guide purpose
This guide defines a **float-only Python grader** for case A.6. The objective is to validate that the model returns structured takeaways that are not only schema-valid, but also **locally coherent** in page-space. In plain terms: each takeaway should stay focused on one nearby region of the book and should not blend distant chapters into one claim.

This guide follows the same structure as the other Curator guides:
1. Prompt package (system + user + inline dataset row).
2. Runtime contract (`sample`, `item`, float return only).
3. Main grader for final pass/fail.
4. Minimal split debug tests (as little as possible, as much as necessary).

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
- Return float only: `1.0` (pass) or `0.0` (fail).
- Read model output from `sample.get("output_text", "")`.
- Parse using strict `json.loads`.
- `item` is the dataset row for this run.

## 4) Main grader (A.6 cluster-locality)
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


def parse_page_range(range_text):
    """Parse a `p<start>-<end>` string into `(start, end)` inclusive, normalized."""
    if not isinstance(range_text, str):
        return None
    match = RANGE_RE.match(range_text)
    if not match:
        return None
    a, b = int(match.group(1)), int(match.group(2))
    return (min(a, b), max(a, b))


def compute_overlap_ratio(span_start, span_end, zone_start, zone_end):
    """Compute fraction of takeaway span that overlaps one target cluster zone."""
    span_len = span_end - span_start + 1
    inter = max(0, min(span_end, zone_end) - max(span_start, zone_start) + 1)
    return inter / span_len


def validate_cluster_locality_constraints(takeaways, item):
    """Validate A.6-specific locality: count, narrow span, and optional cluster anchoring."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        max_span = int(item["max_takeaway_span_pages"])
    except Exception:
        return False

    if expected_n < 1 or max_span < 1 or len(takeaways) != expected_n:
        return False

    cluster_ranges = item.get("required_cluster_ranges", [])
    if not isinstance(cluster_ranges, list):
        return False

    normalized_clusters = []
    for zone in cluster_ranges:
        if not (isinstance(zone, list) and len(zone) == 2):
            return False
        try:
            z1, z2 = int(zone[0]), int(zone[1])
        except Exception:
            return False
        normalized_clusters.append((min(z1, z2), max(z1, z2)))

    anchored = 0
    for takeaway in takeaways:
        if not isinstance(takeaway, dict):
            return False
        for key in REQUIRED_KEYS:
            if key not in takeaway:
                return False

        parsed = parse_page_range(takeaway.get("approx_page_range"))
        if parsed is None:
            return False
        start, end = parsed

        if (end - start + 1) > max_span:
            return False

        if normalized_clusters:
            best = 0.0
            for zone_start, zone_end in normalized_clusters:
                best = max(best, compute_overlap_ratio(start, end, zone_start, zone_end))
            if best >= 0.80:
                anchored += 1

    if normalized_clusters:
        return anchored >= expected_n - 1
    return True


def grade(sample, item):
    """Return 1.0 when baseline schema checks and A.6 locality checks pass."""
    obj = parse_output_json(sample)
    if obj is None:
        return 0.0

    takeaways = get_takeaways_array(obj)
    if takeaways is None:
        return 0.0

    return 1.0 if validate_cluster_locality_constraints(takeaways, item) else 0.0
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

### Test 3 — A.6 locality constraints
```python
import json
import re

RANGE_RE = re.compile(r"^p([0-9]+)-([0-9]+)$")


def parse_output_json(sample):
    """Parse `sample.output_text` into a Python object; return None on parse failure."""
    try:
        return json.loads(sample.get("output_text", ""))
    except Exception:
        return None


def parse_page_range(range_text):
    """Parse a `p<start>-<end>` string into `(start, end)` inclusive, normalized."""
    if not isinstance(range_text, str):
        return None
    match = RANGE_RE.match(range_text)
    if not match:
        return None
    a, b = int(match.group(1)), int(match.group(2))
    return (min(a, b), max(a, b))


def validate_cluster_locality_constraints(takeaways, item):
    """Validate count, max span, and optional cluster anchoring for case A.6."""
    try:
        expected_n = int(item["expected_takeaway_count"])
        max_span = int(item["max_takeaway_span_pages"])
    except Exception:
        return False
    if len(takeaways) != expected_n:
        return False

    clusters = item.get("required_cluster_ranges", [])
    if not isinstance(clusters, list):
        return False

    normalized = []
    for c in clusters:
        if not (isinstance(c, list) and len(c) == 2):
            return False
        normalized.append((min(int(c[0]), int(c[1])), max(int(c[0]), int(c[1]))))

    anchored = 0
    for t in takeaways:
        parsed = parse_page_range(t.get("approx_page_range") if isinstance(t, dict) else None)
        if parsed is None:
            return False
        s, e = parsed
        span = e - s + 1
        if span > max_span:
            return False

        if normalized:
            best = 0.0
            for zs, ze in normalized:
                inter = max(0, min(e, ze) - max(s, zs) + 1)
                best = max(best, inter / span)
            if best >= 0.80:
                anchored += 1

    return anchored >= expected_n - 1 if normalized else True


def grade(sample, item):
    """Return 1.0 when A.6-specific locality constraints pass; else 0.0."""
    obj = parse_output_json(sample)
    if not isinstance(obj, dict) or not isinstance(obj.get("takeaways"), list):
        return 0.0
    return 1.0 if validate_cluster_locality_constraints(obj["takeaways"], item) else 0.0
```

## 6) Recommended debug order
1. Test 1 (JSON parse)
2. Test 2 (root + `takeaways` list)
3. Test 3 (A.6 locality)
