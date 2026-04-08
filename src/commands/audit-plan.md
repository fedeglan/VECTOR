# /audit-plan

Audit the current state of the codebase against the development plan and all project specs.

Run this every 10 merged PRs and at the end of each phase.

## Before you start

Read these files in full:
- CLAUDE.md
- CONTEXT.md
- SESSIONS.md
- docs/DEVELOPMENT_PLAN.md
- docs/api-spec.yaml
- docs/erd.dbml
- docs/architecture.md
- All files in docs/research/

## What to audit

### 1. Plan compliance
For every TASK in DEVELOPMENT_PLAN.md marked as done (check SESSIONS.md):
- Do the files listed in "Files affected" actually exist?
- Does the implementation satisfy the "Done when" criterion?
- Flag any task marked done that does not fully satisfy its criterion.

### 2. API compliance
For every endpoint in api-spec.yaml:
- Does a corresponding router implementation exist?
- Does the path, method, request schema, and response schema match exactly?
- Are the correct error codes returned?

### 3. Schema compliance
For every table in erd.dbml:
- Does a corresponding migration exist?
- Does the migration match the table definition exactly (column names, types, constraints, foreign keys)?
- Does the SQLAlchemy model match the migration?

### 4. Architecture compliance
- Does the folder structure match CLAUDE.md?
- Are all mandatory patterns present throughout the codebase?
- Are any forbidden patterns present anywhere?
- Does the quant package import from backend/? (must not)
- Is there any business logic in routers? (must not)
- Is there any direct DB access outside repositories? (must not)

### 5. Quant compliance (if applicable)
For every MSD in docs/research/:
- Does a corresponding implementation exist in the quant package?
- Do the inputs match the MSD?
- Does the output type, range, and null handling match the MSD?
- Do the known failure modes have handling in the code?

### 6. Test coverage
- Does every router have integration tests?
- Does every service have unit tests?
- Does every quant model have mathematical unit tests?

## Output

Write `docs/audits/audit_<phase>_<YYYY-MM-DD>.md`:

```
# Audit: <phase> — <date>

## Summary
Tasks audited: N
Blockers found: N
Warnings found: N

## Blockers (must fix before next phase)
<numbered list — each with file, description, and required fix>

## Warnings (should fix, not blocking)
<numbered list>

## Passed checks
<summary of what is correct>
```

Log the audit in SESSIONS.md. Report the summary to the human and tell them what must be fixed before proceeding.