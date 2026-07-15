# /upgrade-project

Retrofit an existing VECTOR v1 project (or a compatible repo) to the v2 contract: install the enforcement layer, write POLICY.md, and wire the gates — without touching the frozen design or the code. This is the one brownfield path v2 supports.

## Preconditions
- The project has VECTOR v1 structure (`CLAUDE.md`, `CONTEXT.md`, `docs/` specs) or an equivalent design-frozen state.
- A dedicated GitHub machine user is available for autonomous merges.

## What you do

### 1. Assess
Read the project's specs and `CONTEXT.md`. Identify: the frozen-track artifacts present, the stack, and which VECTOR profile fits (`webapp` | `service-api`). Report what is present and what is missing before changing anything.

### 2. Instantiate POLICY.md
Create it with the human (autonomy level, budgets, breakers, deploy target, notify recipients, `method_version` pin). Recommend starting at **L1** for a retrofitted project regardless of the author's usual default — the shadow-mode telemetry has to be earned on this codebase.

### 3. Install the enforcement layer (files only)
- `.claude/hooks/` — the three hooks + `hooks.json` wiring in `.claude/settings.json` (no read-side deny-rules: writes are hooked, reads must stay open for the reviewer).
- `.github/workflows/` — ci-tests, conformance (endpoints↔OpenAPI, migrations↔ERD), security, coverage-ratchet, test-protection.
- `CODEOWNERS` on the frozen paths + `POLICY.md` (never on `tests/**`).
- `.vector/` skeleton, `ESCALATIONS.md`, the ops-pack skeleton.

### 4. Bootstrap protection
Branch protection on DEV with the required checks; verify the machine user; set the `reviewer-approval` status check.

### 5. Preflight
Run `/preflight-audit`. A retrofitted repo often surfaces coverage gaps (endpoints with no issue, specs with drift) — these are findings to resolve before autonomy, exactly as in a fresh project.

## Hard rules
- Do not modify the existing frozen specs or the application code. This command adds enforcement; it does not redesign.
- If the existing specs are not actually consistent (v1 drift), report it — the human resolves via `/change-scope`. Do not silently "fix" a spec to make the matrix pass.
- The project does not go autonomous until `/preflight-audit` is green.
