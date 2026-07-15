# /promote

The release pipeline (Step 18). Human-invoked. Takes an accepted phase from DEV to production through staging, a smoke gate, and the single production human gate. This is the only path to main/prod — the autonomous loop never touches them.

> **Status (2.0.0):** `/promote`'s reference implementation is the Phase E deliverable and binds at the first real deploy; the `vector-revert` command it references is the Phase B relay-runner's revert and is **not yet shipped**. Until both land, run the pipeline manually — deploy to staging, exercise the smoke rounds, take the human GO, deploy, and rehearse rollback as a hand-authored revert PR through the same gates. Do not pretend a step ran that did not.

## Preconditions
- The phase is accepted (Step 17: 0 P0, 0 P1 or justified deferral, audit clean).
- DEV is green.
- `POLICY.md §13` names the `deploy_target` (`vps-compose` | `aws`).

## Pipeline

### 1. Stage
Deploy the current DEV to **staging** on the project's deploy profile:
- `vps-compose` (reference): compose up on the staging host behind the reverse proxy; staging is a separate compose project seeded with synthetic data.
- `aws`: the equivalent staging environment (same pipeline semantics).
Use the minimal IaC generated at Step 13. Never point staging at production data.

### 2. Smoke gate
Run `/explore` rounds 1 + 3 against **staging**. Any P0 or P1 stops the promotion — back to the loop with auto-filed issues.

### 3. Migration check (if this release touches the schema)
If the release includes an ERD change, confirm the migration playbook was followed (expand-contract, backfill with resume, rehearsed against an anonymized staging snapshot). A schema change without a rehearsed migration does not proceed. See `docs/OPERATIONS.md`.

### 4. Human GO — the single production gate
Present the human with: what is shipping, the staging smoke result, the migration plan if any, and the rollback handle. Wait for an explicit GO. This is the only human gate in production and it is required regardless of autonomy level.

### 5. Production deploy
On GO: deploy to prod, then run post-deploy verification (health checks + a smoke pass).

### 6. Rollback readiness
Confirm the rollback path is ready before you finish: the deploy rollback for the target, plus the `vector-revert <tag>` discipline for the code. If post-deploy verification fails, roll back immediately and report.

## Tag
On success, tag the release and record it. On rollback, record what happened in `docs/OPERATIONS.md`'s ops-journal.

## Hard rules
- No GO, no prod. Terminal-only GO (POLICY §13).
- Secrets come from the environment `.env`, never the repo, never agent context.
- You do not decide to promote — the human invokes this command. You execute the pipeline and stop at the GO gate.
