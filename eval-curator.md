# Agent A — Takeaway Curator Eval Suite Index

## 1) Guide purpose
This document is the entry point for the Curator eval suite. It explains what each case is intended to stress-test and links to case guides that implement float-only graders for OpenAI Evals UI.

The suite is designed to evaluate three dimensions:
- **Structural correctness**: machine-parseable JSON with required fields.
- **Retrieval discipline**: page ranges and locality behavior consistent with instructions.
- **Content quality**: non-trivial, specific, information-rich takeaways.

All case guides are expected to use one consistent structure:
1. Guide purpose
2. Prompt package
3. Grader contract
4. Main grader
5. Split debug tests
6. Recommended debug order

## 2) Core cases
| Case | Primary focus | Expected behavior |
| --- | --- | --- |
| A.1–A.3 | Baseline structure + coverage stability | Valid schema, bounded spans, stable central takeaways. |
| A.4 | Chapter-scoped extraction | Takeaways remain inside provided chapter range. |
| A.6 | Cluster locality | Each takeaway stays local and does not blend distant sections. |
| A.7 | Non-triviality filter | Claims are specific/mechanistic, not motivational filler. |

## 3) Per-case guide files
- `evals_curator_a1_a3_baseline_grader.md`
- `evals_curator_a4_soft_chapter_grader.md`
- `evals_curator_a6_soft_cluster_locality_grader.md`
- `evals_curator_a7_non_triviality_grader.md`
- `evals_curator_grader_template.md`

## 4) Authoring rules (quick)
- Keep baseline helper names consistent across guides.
- Name case-specific helper functions after the use case.
- Add function docstrings in all code snippets.
- Keep debug tests minimal: baseline parse, baseline container, case-specific constraints.
