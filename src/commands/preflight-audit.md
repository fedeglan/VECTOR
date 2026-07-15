# /preflight-audit

The final gate of Act I (Step 15): four tracks that must all pass before the machine is allowed to build autonomously. This is launch authorization — the last human gate before Act II.

## Track 1 — Ambiguity scan
Spawn a fresh-context adversarial read of every issue plus every frozen spec, hunting for:
- Contradictions between issues, or between an issue and a spec.
- Acceptance criteria that are not expressible as an executable command or test.
- Any remaining `[NEEDS CLARIFICATION]` marker in a frozen-track file.

**Hard condition:** zero live markers. Any contradiction or non-executable criterion is a finding that goes back to design (via `/change-scope` if it touches a frozen spec).

## Track 2 — Coverage matrix
Build the cross-artifact matrix and check every direction:
- Every user story → ≥1 endpoint, ≥1 view, ≥1 issue.
- Every endpoint → appears in `api-frontend-reference.yaml` and has ≥1 issue.
- Every view → has ≥1 issue.
- Every entity → covered by a migration issue.

Emit it as a checklist. An orphan in any direction is a finding. (Steps N-A for the active profile drop out of the matrix automatically.)

## Track 3 — Environment dry-run
- Stack boots via `docker-compose up`.
- Empty test suite runs green in CI.
- `gh` authenticated as the machine user, with the right permissions.
- Playwright installed and can launch.
- `POLICY.md` parses fail-fast; all required keys present.
- Notification hook reachable, if configured.

## Track 4 — Hooks red-team + revert rehearsal
Run the hook batteries in-repo and rehearse a rollback:
```bash
python3 .claude/hooks/tests/redteam.py
python3 .claude/hooks/tests/redteam2.py
python3 .claude/hooks/tests/redteam3.py
```
Then prove, live: an agent cannot edit a frozen spec, cannot delete a test, cannot add a dependency silently, and cannot merge past a red check. Finally, rehearse the revert: `vector-revert <tag>` on a throwaway commit, confirming it opens a revert PR through the same gates. **Until the Phase B runner ships, `vector-revert` does not exist** — rehearse the revert manually (a hand-authored revert PR through the same required checks) and note in the go/no-go that the scripted path is pending.

## The gate
Present the four track results to the human as a single go/no-go. All green → the human authorizes launch and Act II begins with `/run-phase`. Any red → fix and re-run; nothing autonomous starts until this passes.

## Hard rule
This gate is not advisory. A red track blocks autonomy. Do not proceed to `/run-phase` on a partial pass.
