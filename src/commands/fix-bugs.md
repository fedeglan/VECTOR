# /fix-bugs

Work the bug backlog by severity. In v2 this runs **autonomously at phase close** (no approval gate to start), but every individual fix still passes through the full build pipeline and its gates — autonomy speeds the *dispatch*, not the *standard*.

## Input
`docs/testing/BUG_BACKLOG.md` — populated by `/explore` and `/report-bug`, each entry with a severity (P0–P3), a screenshot, and (for Explorer findings) the intercepted network log.

## The matrix
- **P0 — flow broken:** highest priority, **one per batch**, fixed immediately. A P0 in production is the hotfix path.
- **P1 — wrong/failed endpoint:** fixed this phase, batched.
- **P2 — state/UX anomaly:** fixed this phase, batched.
- **P3 — visual over threshold:** deferral allowed, logged with a justification.

## Per fix
1. Reproduce from the backlog entry (the screenshot + network log make this deterministic).
2. Diagnose root cause (`/debug` if non-obvious). Fix the cause, not the symptom.
3. Add a regression test that fails before the fix and passes after — mandatory.
4. Ship it through the **full `/ship-issue` gate sequence**: branch, tests, review, CI, merge, tag. A fix is a change like any other; it does not get a shortcut around the gates.
5. Mark the backlog entry resolved with the PR link.

## Autonomy note
At phase close the matrix executes without waiting for human approval to begin — but a P0 that cannot be fixed within budget escalates, a fix that reveals a spec-conflict escalates, and anything requiring a frozen-spec change goes through `/change-scope`. The loop is fast, not unsupervised.

## Hard rules
- Every fix ships a regression test. No exceptions — the coverage ratchet and reviewer enforce it.
- Do not "fix" a failing test by weakening it. If the test is right, fix the code.
- A deferred P3 is logged with a reason; P0/P1 are not deferrable within a phase.
