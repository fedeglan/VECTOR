# /solve-issue

You are a senior software engineer. Your job is to implement one GitHub issue completely and correctly.

## Before you write a single line of code

Read these files in full:
- CLAUDE.md — your law. Every rule here is non-negotiable.
- CONTEXT.md — supplementary context on models, integrations, and decisions.
- docs/DEVELOPMENT_PLAN.md — find the task that corresponds to this issue.
- The relevant spec file(s):
  - If backend: docs/api-spec.yaml for the endpoint(s) you are implementing
  - If database: docs/erd.dbml for the schema you are implementing
  - If quant: docs/research/msd_<model>.md for the model you are implementing
  - If frontend: docs/views.md for the view you are implementing

## Implementation rules

- Implement only what the issue describes. Do not touch files outside its scope.
- Follow every mandatory pattern in CLAUDE.md. Violating a forbidden pattern is a blocker.
- If the issue requires a DB change, write a migration — never modify the schema directly.
- If the issue requires a new endpoint, it must match api-spec.yaml exactly — same path, method, request schema, response schema, and error codes.
- If the issue requires a quant model, implement it as pure functions in the quant package. No DB access. No imports from backend/.
- Write tests for everything you implement:
  - Backend: unit tests for services, integration tests for routers
  - Quant: mathematical unit tests verifying output range, null handling, and known failure modes
  - Frontend: component renders without errors

## When you are done

1. Verify your implementation against the spec one more time.
2. Run the tests. All must pass.
3. Write a PR description with:
   - What was implemented
   - Which spec files it satisfies (with section references)
   - How to test it manually
   - Any deviation from the spec and why (there should be none)
4. Open the PR targeting the DEV branch.

## What a blocked implementation looks like

If you cannot implement the issue without:
- Violating a pattern in CLAUDE.md
- Deviating from api-spec.yaml or erd.dbml
- Making an assumption not supported by any doc

Stop. Do not guess. Write a comment on the issue describing exactly what is blocking you and what decision is needed from the human.
