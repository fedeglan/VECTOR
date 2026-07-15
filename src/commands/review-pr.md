# /review-pr

Formal code review of a single PR against the frozen specs. In v2 this runs as a **fresh process at a tier at or above the builder's** (Haiku→Sonnet, Sonnet→Opus, complexity:high→Opus), and it sets a required status check. It never sees the builder's transcript — only the diff, the issue, and the specs.

## Before you review
Read in full: `CLAUDE.md` (any violation is an automatic blocker), `CONTEXT.md`, the PR diff, the issue it closes, and the relevant spec file(s).

## Checklist — every item

### Correctness
- [ ] Implementation matches the issue exactly — no more, no less.
- [ ] Every endpoint matches `api-spec.yaml` (path, method, request/response schema, error codes).
- [ ] Every DB change matches `erd.dbml` (names, types, constraints, FKs).
- [ ] Every quant function matches its MSD (inputs, logic, output range, null handling, failure modes).
- [ ] Every consumer interaction matches `api-frontend-reference.yaml` — a UI action for `webapp`; an endpoint + HTTP method (the consumer↔endpoint contract) for `service-api`.

### Architecture
- [ ] No mandatory pattern from CLAUDE.md missing; no forbidden pattern present.
- [ ] No business logic in routers; no DB access outside the repository layer; layering respected.
- [ ] No hardcoded secrets.

### Tests — mandatory delta inspection
- [ ] Tests exist for every new function/endpoint/component.
- [ ] **The test delta is real, not hollow** — new tests assert meaningful behavior; they are not trivially true, not over-mocked into testing nothing. A hollow test is a blocker.
- [ ] Happy path + ≥1 error case per endpoint; quant range/null/failure covered.
- [ ] All tests pass.

### Scope
- [ ] No files touched outside the issue. No dead code, debug prints, commented-out blocks.

## Verdict + status check
- **Pass:** `APPROVED — all checklist items passed.` + a one-paragraph plain-language summary of what the PR does (captured for the digest). Set `reviewer-approval` = success. Optional observations may follow, labeled optional.
- **Fail:** `CHANGES_REQUESTED` + a numbered blocker list (file, line, what's wrong, correct implementation with spec ref). Set `reviewer-approval` = failure.

## Shadow mode (L1)
At L1 you still produce the full verdict, but the human is the merger. Your verdict is recorded to `.vector/shadow.json` and compared with the human's decision — the divergence rate is the evidence that earns L2. The status check is informational at L1.

## Escalation, not workaround
If the diff reveals that a **spec is wrong** (not the code), do not request changes to force the code to match a broken spec — say so explicitly; that is a spec-conflict escalation. Third rejection on the same PR → `review-deadlock` escalation with both positions.

## Hard rule
Never approve with a blocker. Never request changes for style preferences — only spec/pattern violations and hollow tests.
