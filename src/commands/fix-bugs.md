# /fix-bugs

Full bug resolution pipeline: analyze the backlog, propose a prioritized fix plan, wait for human review, then execute.

This command combines triage and fix into a single workflow:
1. **Analyze** — read backlog, deduplicate, enrich, categorize, prioritize
2. **Plan** — propose a fix order and present to human
3. **Review gate** — human approves (or adjusts) the plan
4. **Execute** — fix bugs one by one with gitflow + regression tests
5. **Verify** — re-run /test-plan to confirm no regressions

## Usage

```
/fix-bugs               # process all open bugs
/fix-bugs BUG-003       # fix a specific bug
/fix-bugs P0 P1         # fix only P0 and P1 severity
```

## Before you start

Read:
- `docs/testing/BUG_BACKLOG.md`
- CLAUDE.md, CONTEXT.md, SESSIONS.md

---

## Phase 1 — Analyze

### Step 1 — Parse the backlog

Find all bugs with status `🟡 open`. For each:
- Read the report fields
- Note quick-mode bugs that need enrichment

### Step 2 — Enrich quick-mode bugs

For bugs captured with `-q`, gather missing info:
- Read the code for the affected view/module
- Infer probable steps to reproduce
- Identify expected vs actual by cross-referencing PRD/spec

If critical info is still missing for a P0/P1 bug, flag it and ask the human before the plan is finalized.

### Step 3 — Deduplicate and group

Two bugs are duplicates if:
- Same view + same action + same symptom → merge (keep earlier BUG-ID, mark later as `⚫ duplicate of BUG-<NNN>`)
- Same symptom, different roles → NOT duplicates (could be an RBAC issue)
- Different views but same root cause → link as "related to" (do not merge)

### Step 4 — Categorize and estimate

For each non-duplicate bug, assign:
- **Category**: backend | frontend | quant | infra | UX
- **Probable files**: list specific files based on code inspection
- **Estimated effort**: 30min / 1h / 2h / 4h
- **Risk**: low (isolated) / medium (touches shared code) / high (touches critical path)

### Step 5 — Priority matrix

Adjust severity-based priority by current phase:

| Severity | MVP phase | V1 phase | V2+ phase |
|----------|-----------|----------|-----------|
| P0 | Fix now, block phase | Fix now | Fix now |
| P1 | Fix this phase | Fix this phase | Defer to hotfix if urgent |
| P2 | Fix if time, else defer | Fix in next phase | Defer |
| P3 | Defer to V1 polish | Fix if time | Defer |
| IMP | Long backlog, never block | Long backlog | Long backlog |

Phase acceptance requires:
- 0 P0 open
- 0 P1 open (unless explicitly deferred by human with justification)

---

## Phase 2 — Propose plan

### Step 6 — Build fix batches

Group bugs into batches that can be fixed together:

| Severity | Max batch size | Strategy |
|----------|---------------|----------|
| P0 | 1 per batch | Isolated, no bundling |
| P1 | 2-3 per batch | Bundle if same module |
| P2 | 3-5 per batch | Bundle by category |
| P3 | 5-10 per batch | Polish pass |

Sequence batches: P0 first, then P1, then P2, then P3. Within a batch, order by dependency.

### Step 7 — Present the plan to the human

```
🔍 Bug Analysis — <date>

Open bugs in backlog: <N>
  · P0 blockers:     <N>
  · P1 major:        <N>
  · P2 minor:        <N>
  · P3 cosmetic:     <N>
  · IMP improvements: <N>

Processed:
  · Duplicates merged:    <N>
  · Details enriched:     <N>
  · Needs more info:      <N>  ⚠️

Proposed fix plan:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BATCH 1 — P0 blockers (must fix now)
  BUG-007: App crashes on login with special chars
    · Category: backend
    · Files:    backend/api/routers/auth.py, backend/schemas/auth.py
    · Effort:   1h · Risk: medium
    · Branch:   fix/BUG-007-login-special-chars

BATCH 2 — P1 major (2 bugs, same module)
  BUG-003: Retry button crashes on failed report
    · Category: backend
    · Files:    backend/api/routers/reports.py
    · Effort:   45min · Risk: low
  BUG-005: Report status never updates to failed
    · Category: backend
    · Files:    backend/services/report_service.py
    · Effort:   1h · Risk: medium
    · Branch:   fix/batch-2026-04-16-reports

BATCH 3 — P2 polish (4 bugs, UX cluster)
  BUG-002: Table sort reversed on first load
  BUG-009: Loading spinner too small on mobile
  BUG-011: Modal doesn't close on ESC
  BUG-014: Empty state copy is confusing
    · Category: frontend
    · Effort:   2h total · Risk: low
    · Branch:   fix/batch-2026-04-16-polish

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Deferred to next phase:
  · <N> P3 cosmetic bugs
  · <N> IMP improvements → added to long backlog

Needs more info (cannot fix without clarification):
  · BUG-<NNN>: <title> — <what's missing>

Total estimated time: <X>h <Y>min

Approve this plan? Options:
  [y] approve and execute
  [adjust] I want to change the order or batches
  [defer <IDs>] mark specific bugs as deferred with justification
  [cancel] stop here, I'll think about it
```

### Step 8 — Update backlog with triage metadata

For every analyzed bug, update its entry in BUG_BACKLOG.md:

```markdown
## BUG-<NNN>: <title>
**Status**: 🔵 triaged
**Priority**: P0 / P1 / P2 / P3 / IMP
**Category**: backend | frontend | quant | infra | UX
**Probable files**: <list>
**Estimated effort**: <time>
**Risk**: low / medium / high
**Batch**: <batch label>
**Duplicates of**: BUG-<NNN> (if applicable)
**Related to**: BUG-<NNN>, BUG-<NNN> (if grouped)
**GitHub issue**: (to be created on execution)
...
```

### Step 9 — Wait for human approval

Do NOT proceed to execution until the human explicitly approves. If they adjust the plan, re-present and re-confirm.

---

## Phase 3 — Execute

For each approved batch, execute in sequence. One batch at a time.

### Step 10 — Create branch

```bash
git checkout DEV
git pull origin DEV
git checkout -b <branch-name-from-plan>
```

### Step 11 — Create GitHub issues (if not yet created)

For each bug in the batch:

```bash
gh issue create \
  --title "BUG-<NNN>: <title>" \
  --body "<full bug content from backlog + triage metadata>" \
  --label "type:fix,priority:<P0-P3>,phase:<current>,bug" \
  --milestone "<current phase>"
```

Update BUG_BACKLOG.md with the GitHub issue number for each bug.

### Step 12 — Reproduce the bug

For each bug in the batch:
1. Start the system (use `/how-to-navigate` steps)
2. Follow the exact reproduction steps from the backlog
3. Confirm you see the same actual behavior

If a bug is NOT reproducible:
```
⚠️ BUG-<NNN> not reproducible

Followed the steps from the backlog. Did not observe the reported issue.

Possible explanations:
- Environment difference
- Already fixed by a later commit
- Needs more detail from reporter

Action: Comment on GitHub issue asking for more info.
        Skip this bug in the current batch.
        Mark as "needs repro" in backlog.
```

### Step 13 — Identify root cause

Do NOT fix the symptom — find the real cause:
- Trace the failing action from UI → API → service → DB
- Check git log for recent changes to affected files
- Run related tests — did they miss the case?
- Check CONTEXT.md for related ADRs

Write a 1-2 sentence root cause summary for each bug.

### Step 14 — Implement the fix

Same discipline as `/solve-issue`:
- Touch only files needed to fix the bug
- Respect all patterns in CLAUDE.md
- Never refactor unrelated code
- Never modify specs to match broken code (that's a `/change-scope` situation)

### Step 15 — Add regression test

**Mandatory: every fix includes a test that would have caught the bug.**

For each bug:
- **Unit bug**: unit test exercising the broken input
- **Integration bug**: integration test for the failing flow
- **E2E bug**: Playwright test for the scenario
- **UX bug**: visual regression test for view + viewport combination

Test naming: `test_bug_<NNN>_<short_desc>` so the link to the original bug is preserved.

Example:
```python
def test_bug_003_retry_button_no_crash(client, failed_report):
    """Regression test for BUG-003.
    Previously, clicking Retry on a failed report raised KeyError.
    """
    response = client.post(f"/reports/equity/{failed_report.id}/retry")
    assert response.status_code == 200
```

### Step 16 — Verify

Run reproduction steps again — bug should be gone.

Run targeted test suite:
```bash
pytest tests/unit/<affected> tests/integration/<affected> -v
cd frontend && npm run test:unit -- <affected>
npx playwright test --grep <related>
```

All tests must pass. If anything else broke, investigate.

### Step 17 — Commit and PR

```bash
git add -A
git commit -m "fix(BUG-<NNN>): <short description>

Root cause: <1-2 sentences>
Regression test: <test name>

Closes #<issue-number>"

git push origin <branch-name>
```

Open PR:
```bash
gh pr create \
  --base DEV \
  --title "fix: <batch label or single bug title>" \
  --body "$(cat <<EOF
Fixes: <list of BUG-IDs with #issue numbers>

## Bugs resolved
<per bug: title, root cause, files changed, regression test>

## Verification
- [x] All bugs reproduced on DEV before fixing
- [x] Fixes applied
- [x] Reproduction steps no longer trigger bugs
- [x] Regression tests added and passing
- [x] No other tests broke

## How to test manually
<steps>
EOF
)"
```

### Step 18 — Wait for human review, merge, cleanup

Same as `/ship-issue`:
- Wait for human approval
- `gh pr merge --merge --delete-branch`
- `git checkout DEV && git pull origin DEV`

### Step 19 — Update backlog

For each fixed bug:
```markdown
## BUG-<NNN>: <title>
**Status**: 🟢 fixed
**Fixed in**: PR #<N> on <date>
**Regression test**: <path/to/test::test_name>
**Root cause**: <1-2 sentences>
...
```

### Step 20 — Close GitHub issues

Done automatically via "Closes #" in commit, but verify:
```bash
gh issue view <issue-number>  # should show: Closed
```

### Step 21 — Log in SESSIONS.md

```markdown
### Bug fix session — <date>

Batch: <label>
Fixed <N> bugs:
- BUG-<NNN>: <title> → PR #<N> ✅ · regression test added
- BUG-<NNN>: <title> → PR #<N> ✅ · regression test added
- BUG-<NNN>: <title> → skipped (not reproducible, info requested)

Remaining open bugs:
- P0: <N> (must be 0 before phase acceptance)
- P1: <N>
- P2: <N>
- P3: <N>

Next action:
- If more batches pending: /fix-bugs to process next
- If all critical done: /test-plan to verify no regressions
- If phase acceptance ready: announce to human
```

---

## Phase 4 — Verify

After all approved batches are merged:

### Step 22 — Re-run /test-plan

Run the full test suite again to verify:
- All previously passing tests still pass
- All new regression tests pass
- No new failures introduced by the fixes

```
/test-plan
```

### Step 23 — Phase acceptance check

```
Phase acceptance status — <phase>

🔴 P0 bugs open: <N> (must be 0)
🟠 P1 bugs open: <N> (must be 0 or explicitly deferred)
🟡 P2 bugs open: <N>
🟢 P3 bugs open: <N>

Test suite status: ✅ all layers passing / ❌ <N> regressions

Phase acceptance: <BLOCKED | READY>

<If READY:>
✅ All phase acceptance criteria met. Formally accept this phase and move to next?

<If BLOCKED:>
Still blocking:
1. <blocker>
2. <blocker>
Run /fix-bugs to address remaining issues.
```

---

## What you do NOT do

- Never skip the analysis phase — going straight to fixes misses duplicates and smart batching
- Never close a bug without a fix AND a regression test
- Never silently downgrade severity — the human owns severity, you own categorization
- Never batch P0 with anything else — they deserve focused attention
- Never modify the specs (api-spec.yaml, erd.dbml) to make a bug "not a bug" — that's `/change-scope`
