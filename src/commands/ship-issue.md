# /ship-issue

Full pipeline: implement an issue and review it in one pass before the human sees it.

This command runs `/solve-issue` followed immediately by `/review-pr` in sequence. The PR is only opened after the internal review passes.

## Execution order

### Stage 1 — Implement (Coder)
Follow the full `/solve-issue` protocol:
- Read CLAUDE.md, CONTEXT.md, DEVELOPMENT_PLAN.md, and all relevant specs.
- Implement the issue completely.
- Write and run all tests.
- Do not open a PR yet.

### Stage 2 — Self-review (Reviewer)
Follow the full `/review-pr` protocol against your own implementation:
- Run through every item on the review checklist.
- If any blocker is found: fix it immediately and re-run the checklist from the top.
- Repeat until the checklist passes completely.

### Stage 3 — Open PR
Only after Stage 2 passes with zero blockers:
- Write the PR description:
  - What was implemented
  - Which spec files it satisfies (with section references)
  - Confirmation that the internal review passed and all checklist items were verified
  - How to test it manually
- Open the PR targeting the DEV branch.
- Add the label `ready-for-human-review`.

## What a blocked pipeline looks like

If Stage 1 hits a blocker that cannot be resolved without a human decision:
- Do not open a PR.
- Write a comment on the issue: `BLOCKED — <exact description of what is unclear and what decision is needed>`.
- Stop.

Do not guess. Do not make assumptions not supported by CLAUDE.md, CONTEXT.md, or the spec files.
