# /development-plan

Generate a detailed, task-by-task development plan for this project.

## Before you start

Read these files in full before writing anything:
- CLAUDE.md
- CONTEXT.md
- docs/PRD.md
- docs/api-spec.yaml
- docs/erd.dbml
- docs/architecture.md
- All files in docs/research/ (if any)

## What to produce

Write `docs/DEVELOPMENT_PLAN.md` with the following structure:

### Phases
Organize all work into phases where each phase is independently deployable:
- **MVP** — the minimum that proves the core value proposition works end to end
- **V1** — the full first version as defined in the PRD scope
- **V2+** — explicitly deferred features (from PRD "out of scope")

### Per-phase: task list
For each task:
```
### TASK-NNN: <title>
Phase: MVP | V1 | V2
Type: feat | fix | chore | infra
Depends on: TASK-NNN, TASK-NNN (or "none")
Files affected: <list of files to create or modify>
Done when: <concrete, verifiable criterion — not "it works">
```

### Build order
Tasks must follow this dependency order:
1. Infrastructure (Docker, DB, migrations)
2. Backend models and repositories
3. Backend services
4. Backend routers and API
5. Quant package (if applicable)
6. Frontend components
7. Frontend-backend integration
8. End-to-end tests

## Rules
- Do not write any code. This is a planning step only.
- Every endpoint in api-spec.yaml must map to at least one task.
- Every table in erd.dbml must map to at least one task.
- Every MSD in docs/research/ must map to at least one task.
- No task should take more than one day of focused work. Split if needed.
- The MVP phase must be runnable end-to-end with real data, not mocks.
