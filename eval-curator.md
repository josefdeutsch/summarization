# Agent A — Takeaway Curator Eval Guide (OpenAI Evals Web Interface)

This guide replaces the old text draft and keeps one coherent reference for Curator eval design.

## 1) Core eval suite (rearranged)

| Case ID | Scenario | What it tests | Expected behavior |
| --- | --- | --- | --- |
| **A.1** | Run Curator on one uploaded book with a general instruction (e.g., “Extract main takeaways from the book”). | FileSearch integration + machine-valid JSON output. | Valid JSON, 4–8 takeaways, required fields present, `approx_page_range` format valid. |
| **A.2** | Repeat exactly the same instruction on the same book. | Structural determinism (schema stability). | Schema unchanged and count range stable; minor wording differences allowed. |
| **A.3** | Run Curator on the full book with broad instruction. | Baseline clustering quality without hard scope constraints. | Takeaways reflect major themes; page spans are local (not book-wide). |
| **A.4** | Instruction restricts scope to one chapter or merged multi-chapter interval. | Scoped retrieval behavior + chapter-boundary discipline. | Takeaways remain within expected chapter range under soft overlap thresholds. |
| **A.6** | Book contains clearly separated conceptual clusters in distant regions. | Cluster-locality behavior: avoid merging distant regions in one takeaway. | Each takeaway maps to one local conceptual region and one contiguous page span. |
| **A.7** | Book is mainly motivational/narrative. | Non-triviality filter. | Avoid platitudes; keep structured claims/mechanisms. |
| **A.8** | Technical/structured nonfiction book. | Mechanism/framework extraction quality. | Capture concrete models and distinctions, not vague summaries. |
| **A.9** | Repeat same book + same instruction (third run). | Stability under repeated retrieval. | Concepts/page bands stay broadly consistent; no extreme drift. |
| **A.10** | Slightly reword instruction with same intent. | Prompt-phrasing robustness. | Structure and clustering principle remain stable. |

---

## 2) Per-case guide files

Keep each case guide in its own Markdown file. `eval-curator.md` is the suite index only.

- A.4 guide: `evals_curator_a4_soft_chapter_grader.md`
- A.6 guide: `evals_curator_a6_soft_cluster_locality_grader.md`

- Reusable case template: `evals_curator_grader_template.md`

For future cases (A.1, A.2, A.3, A.7, A.8, A.9, A.10), create one dedicated `.md` per case and link it here.
