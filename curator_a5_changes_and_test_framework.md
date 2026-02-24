# Curator A.5 — Change Summary and Test Framework Notes

## Purpose
This short document explains:
1. **What was changed** for A.5.
2. **How the float-only test framework works** end-to-end.

---

## What changed

### 1) New A.5 grader guide was introduced
- Added a dedicated guide for **A.5 soft page-band scope grading**.
- The guide mirrors the A.4 structure so evaluators can reuse the same mental model.
- It standardizes one contract: `grade(sample, item) -> float` with only `1.0` (pass) or `0.0` (fail).

### 2) Scope switched from chapter bounds to page-band bounds
- A.4 used chapter fields (e.g., `expected_chapter_start`, `expected_chapter_end`).
- A.5 uses page-band fields:
  - `expected_page_start`
  - `expected_page_end`
  - `expected_takeaway_count`
- Output still relies on each takeaway’s `approx_page_range` (e.g., `p84-90`).

### 3) Same overlap logic, new target interval
- For each takeaway range `[a, b]`, overlap with expected interval `[S, E]` is computed using inclusive page math.
- Hard floor rule: fail if any takeaway has overlap ratio `< 0.5`.
- Quality rule: pass only if at least `N-1` takeaways have overlap ratio `>= 0.8`.

---

## How the test framework works

## A) Runtime inputs
- `sample`: model output payload (read text from `sample.get("output_text", "")`).
- `item`: dataset row containing expected config and bounds.

## B) Evaluation pipeline (single main grader)
The main grader runs deterministic checks in this order:
1. Parse output text as JSON.
2. Validate root object shape (`dict`) and `takeaways` list presence.
3. Validate dataset config (`expected_takeaway_count`, `expected_page_start`, `expected_page_end`).
4. Enforce exact takeaway count.
5. Enforce required takeaway keys.
6. Validate `approx_page_range` format (`p<start>-<end>`).
7. Compute overlap ratio per takeaway and enforce thresholds.
8. Return float score (`1.0` or `0.0`).

## C) Debug framework (8 split tests)
To isolate failures quickly, the guide also provides eight micro-graders:
1. JSON parse validity.
2. Root object + takeaways array.
3. Required field presence.
4. Dataset configuration validity.
5. Exact takeaway count match.
6. Page-range format validity.
7. Hard-floor overlap (`>= 0.5`).
8. Soft-overlap quality (`>= 0.8` for `N-1`).

This split lets you identify whether a failure is due to format, schema, config, or overlap behavior.

---

## Why float-only matters
- Keeps grading output machine-simple and deterministic.
- Avoids mixed return types (e.g., dict sometimes, float other times).
- Works cleanly with pass/fail aggregation and regression checks.

---

## Quick implementation checklist
- Keep function signature: `def grade(sample, item):`
- Read from `sample.get("output_text", "")`
- Parse with `json.loads(output_text)`
- Return only `1.0` or `0.0`
- Keep overlap math inclusive (`+1` in intersection and length)
