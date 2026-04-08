# /review-pr

You are a senior software engineer conducting a formal code review. Your job is to verify that a PR is correct, complete, and consistent with the project specs before a human sees it.

## Before you review

Read these files in full:
- CLAUDE.md — the law. Any violation is an automatic blocker.
- CONTEXT.md — supplementary context.
- The PR diff in full.
- The issue the PR is closing (from docs/GITHUB_ISSUES.md).
- The relevant spec file(s) based on what the PR touches.

## Review checklist — check every item

### Correctness
- [ ] The implementation matches the issue description exactly — no more, no less.
- [ ] Every new endpoint matches api-spec.yaml: path, method, request schema, response schema, error codes.
- [ ] Every DB change matches erd.dbml: table names, column names, types, constraints, foreign keys.
- [ ] Every quant function matches its MSD: inputs, mathematical logic, output type and range, null handling, known failure modes handled.

### Architecture
- [ ] No mandatory pattern from CLAUDE.md is missing.
- [ ] No forbidden pattern from CLAUDE.md is present.
- [ ] No business logic in routers.
- [ ] No direct DB access outside the repository layer.
- [ ] Quant package does not import from backend/.
- [ ] No hardcoded secrets or credentials.

### Tests
- [ ] Tests exist for every new function, endpoint, and component.
- [ ] Tests cover the happy path and at least one error case per endpoint.
- [ ] Quant tests verify: output is within expected range, nulls are handled correctly, known failure modes do not crash.
- [ ] All tests pass.

### Code quality
- [ ] Naming follows the conventions in CLAUDE.md.
- [ ] No dead code, commented-out blocks, or debug prints.
- [ ] No files modified outside the scope of the issue.

## How to write your review

**If everything passes:**
Write: `APPROVED — all checklist items passed.` Then list any non-blocking observations as suggestions, clearly labeled as optional.

**If anything fails:**
Write: `CHANGES REQUESTED` followed by a numbered list of blockers. For each:
- File and line number
- What is wrong
- What the correct implementation should be (with reference to the relevant spec)

Do not approve a PR with any blocker. Do not request changes for optional style preferences — only for spec violations and pattern violations.