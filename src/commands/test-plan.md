# /test-plan

Full testing pipeline for a phase close (MVP, V1, V2, etc.). Claude Code audits the existing test corpus, writes what's missing, executes the complete test suite, and produces a detailed report.

This is ONE command that does three things end-to-end:
1. **Audit** the existing test corpus and identify gaps
2. **Complete** the suite with new tests (fix broken, expand gaps, add missing layers)
3. **Execute** the full suite, generate reports, log results

Run this at the start of each phase's testing cycle.

## Before you start

Read:
- CLAUDE.md, CONTEXT.md, SESSIONS.md (latest entries)
- Design documents (for context on what was built):
  - docs/PRD.md (user types, permissions, core actions)
  - docs/views.md (every view)
  - docs/api-spec.yaml (every endpoint)
  - docs/api-frontend-reference.docx (action-to-endpoint mapping)
  - docs/erd.dbml (data model)
  - docs/research/*.md (quant models, if any)
  - docs/architecture.md (patterns)

Verify test dependencies:
- Backend: pytest + pytest-asyncio + pytest-cov + pytest-xdist + httpx + bandit + pip-audit
- Frontend: vitest (or jest) + React Testing Library + eslint-plugin-security
- E2E: Playwright (`npm install -D @playwright/test && npx playwright install`)
- Security: gitleaks (`brew install gitleaks` if missing)

If anything is missing, install it before proceeding.

---

## Phase 1 — Audit existing corpus

### Step 1 — Inventory

```bash
# Find all test files
find tests -name "test_*.py" -o -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" | sort

# Count tests per file
for f in $(find tests -name "test_*.py"); do
  echo "$f: $(grep -c "^def test_\|^async def test_" $f) tests"
done

# Inventory production code
find backend -name "*.py" -not -path "*/tests/*"
find backend/api/routers -name "*.py" | xargs grep -E "^@router\."
find frontend/src -name "*.jsx" -o -name "*.tsx"
```

Build a map: `test file → module tested → test count → test type (unit/integration/other)`.

### Step 2 — Run baseline

```bash
# Backend
cd backend
pytest tests/ -v --cov=backend --cov-report=json --cov-report=term --durations=20

# Frontend
cd ../frontend
npm run test -- --coverage --reporter=json
```

Capture: total tests, pass/fail, line + branch coverage per module, slowest 20, any flaky tests.

### Step 3 — Coverage assessment

For every production module, assess:
- ✅ **good**: >80% line + >70% branch coverage, tests exist for all public methods
- ⚠️ **gap**: 50-80% line coverage, obvious missing cases (error paths, edge cases)
- ❌ **insufficient**: <50% line coverage or critical paths untested
- 🚨 **untested**: 0% coverage, no test file exists

### Step 4 — Qualitative audit

Coverage numbers lie. Flag test smells:
- Tests without assertions
- Tests that always pass (assert True, assert not None on guaranteed non-null)
- Tests that mock away the thing being tested
- Tests with hardcoded delays (`sleep()`) — probably flaky
- Tests that depend on execution order
- Tests that leave state in the DB (no teardown)
- Skipped tests (`@pytest.mark.skip`) — why?

Also check coverage quality:
- Happy path for every public method?
- 4xx responses tested for every mutation (401, 403, 404, 422, 409)?
- Edge cases (empty inputs, null, boundary values, unicode)?
- Quant-specific: output range, known failure modes from MSD, mathematical properties?

### Step 5 — Layer gap analysis

Which layers of the testing pyramid exist? Which don't?

| Layer | Existing | Expected | Status |
|-------|----------|----------|--------|
| Unit (backend) | N | N | ⚠️ partial |
| Unit (frontend) | N | N | ⚠️ partial |
| Unit (quant) | N | N | ⚠️ partial |
| Integration | N | N | ⚠️ partial |
| Security | 0 | N | ❌ missing entirely |
| E2E | 0 | N | ❌ missing entirely |
| UX/UI visual | 0 | N | ❌ missing entirely |
| Performance | 0 | N | ❌ missing entirely |

"Expected" counts:
- Unit: every public function/method/component
- Integration: every endpoint + every cross-service flow
- E2E: every primary user flow in PRD
- UX/UI: every view × viewport × role (default state minimum)
- Security: items in the security checklist below
- Performance: critical paths only (V1+)

---

## Phase 2 — Complete the suite

Organize the work in three streams. All three must be addressed before execution.

### Stream A — Fix broken tests

For each test flagged as broken, misleading, or smelly in the audit:
- Rewrite with proper assertions
- Split tests that do too much
- Delete tests that are duplicates or meaningless
- Unskip tests that were skipped without justification (or document why they should stay skipped)

**Rule:** Fix before writing new. Broken tests give false confidence.

### Stream B — Expand existing layers (unit + integration)

Fill coverage gaps in modules flagged ⚠️ or ❌. Priority:
1. Modules with ❌ insufficient → critical gaps
2. Modules with ⚠️ gap on error paths
3. Modules with ⚠️ gap on edge cases
4. Modules with low branch coverage

Write tests that:
- Cover every public method's happy path
- Cover at least one error case per mutation endpoint
- Cover edge cases (empty, null, boundary, unicode)
- For quant: output range + MSD failure modes + mathematical properties
- For frontend: renders + loading/error/empty states + interaction handlers

### Stream C — Build missing layers

**C.1 — Security tests** (new layer, ~20-40 tests)

Authentication:
- [ ] Valid login → JWT issued, cookie flags correct (HttpOnly, Secure, SameSite)
- [ ] Invalid credentials → 401, no user enumeration
- [ ] Expired token → 401
- [ ] Malformed token → 401 without crash
- [ ] Refresh flow → new access token, old refresh invalidated
- [ ] Logout → refresh revoked, cannot reuse

Authorization (RBAC matrix):
- [ ] Every endpoint × every role → expected 200/403 matches PRD permissions
- [ ] IDOR: user A cannot access user B's data
- [ ] Privilege escalation: regular user cannot hit admin endpoints
- [ ] Frontend route guards match backend enforcement

Input validation:
- [ ] SQL injection payloads on every string input → ORM rejects
- [ ] XSS payloads → sanitized on render
- [ ] Path traversal (`../../../etc/passwd`) → rejected
- [ ] Mass assignment (extra fields) → ignored or rejected
- [ ] Oversized payloads → rejected before DB

Secrets & config:
- [ ] `gitleaks detect` → 0 secrets in repo
- [ ] `.env.example` has placeholders, never real values
- [ ] API keys never logged
- [ ] Stack traces never leaked in production responses

Transport & CORS:
- [ ] CORS allows only configured origins
- [ ] Production cookies: HttpOnly + Secure + SameSite
- [ ] Rate limiting on auth endpoints

Dependencies:
- [ ] `pip-audit` → 0 critical CVEs
- [ ] `npm audit` → 0 critical CVEs

Static analysis:
- [ ] `bandit -r backend -ll` → 0 high-severity
- [ ] `eslint --plugin security` → 0 errors

**C.2 — E2E tests** (new layer, one flow per PRD primary action)

For every primary user flow, write a Playwright spec:
```
test('E2E-N: <flow>', async ({ page }) => {
  // 1. <action> → expect <observable outcome>
  // 2. <action> → expect <observable outcome>
  // Pass criteria: <final state>
});
```

Cover:
- Core happy path login → goal
- Permission boundaries (role-based visibility)
- Error recovery (invalid → fix → resubmit)
- State persistence (refresh, data survives)
- Session lifecycle (logout → login → state)

**C.3 — UX/UI visual tests** (new layer)

Matrix: every view × viewports (desktop 1440×900, tablet 768×1024, mobile 375×667) × every role × states (default, loading, error, empty, populated).

For each cell:
- `toHaveScreenshot()` comparison against baseline
- No layout shift
- Keyboard reachable
- WCAG AA contrast (4.5:1)
- No text overflow

Run accessibility checks with axe-core.

Budget-aware sampling if full matrix exceeds time budget:
- Every view × default state × every role × desktop (full coverage of core case)
- Critical views × all viewports × default state (responsive)
- Sampling of error/empty states on a handful of views

**C.4 — Performance baseline** (V1+ only, new layer)

- Lighthouse per view (TTFB, FCP, LCP)
- k6 or locust for API (p50, p95, p99)
- DB query analysis via `pg_stat_statements`
- Frontend bundle size

---

## Phase 3 — Execute the suite

### Time budget (hard ceiling: 20 minutes)

| Layer | Budget | If exceeded |
|-------|--------|-------------|
| Unit | ≤ 60s | Parallelize with pytest-xdist / vitest threads |
| Integration | ≤ 3m | Share fixtures, in-memory DB where safe |
| Security | ≤ 2m | Static checks + sampled requests |
| E2E | ≤ 5m | Critical path only; full suite nightly |
| UX/UI | ≤ 3m | Sample viewports, not full matrix |
| Performance | ≤ 5m | Smoke only; detailed benchmarks offline |
| **Target total** | **≤ 20m** | Present Fast vs Thorough plan variants |

If the projected runtime exceeds budget, report to the human and offer two plan variants:
- **Fast plan** (≤20m): critical paths only, deep coverage offline
- **Thorough plan** (full matrix): for final phase acceptance only

Let the human choose. Default to Fast for iterative phase testing; Thorough for formal phase acceptance.

### Execution order (gate each layer)

**Layer 1 — Unit** (budget: 60s)
```bash
cd backend && pytest tests/unit -v -n auto --cov=backend --cov-report=json
cd ../frontend && npm run test:unit -- --coverage
cd ../backend && pytest tests/quant -v -n auto --cov=backend.quant
```
Gate: if unit fails, stop. Do not proceed.

**Layer 2 — Integration** (budget: 3m)
```bash
docker compose -f docker-compose.test.yml up -d db
alembic -x db=test upgrade head
pytest tests/integration -v
docker compose -f docker-compose.test.yml down
```
Gate: if integration fails, stop.

**Layer 3 — Security** (budget: 2m, can run in parallel with Layer 2)
```bash
gitleaks detect --source . -v --report-format json --report-path reports/gitleaks.json
cd backend && pip-audit --format json > ../reports/pip-audit.json
cd ../frontend && npm audit --json > ../reports/npm-audit.json
cd ../backend && bandit -r . -ll -f json -o ../reports/bandit.json
cd ../frontend && npx eslint --plugin security --format json -o ../reports/eslint-security.json .
cd ../backend && pytest tests/security -v
```
Gate: any critical-severity finding stops the pipeline.

**Layer 4 — E2E** (budget: 5m)
```bash
docker compose up -d && sleep 10
docker compose exec backend python -m backend.scripts.seed --env test
cd frontend && npx playwright test --reporter=json,html --workers=4
docker compose down
```
Gate: if E2E fails, stop.

**Layer 5 — UX/UI visual** (budget: 3m)
```bash
docker compose up -d && sleep 10
cd frontend
npx playwright test --grep @visual --update-snapshots=missing
npx playwright test --grep @a11y
```

**Layer 6 — Performance** (budget: 5m, V1+ only)
```bash
npx lighthouse http://localhost:5173 --output=json --output-path=./reports/lighthouse.json
k6 run tests/performance/api_load.js --summary-export=reports/k6.json
docker compose exec db psql -U postgres -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

### When tests fail

Do NOT auto-fix. Report to the human first. Automated fixes risk masking real bugs or modifying tests to match broken code.

If the human confirms a fix:
- Identify root cause (broken code vs broken test vs flaky)
- Code broken: follow `/debug` protocol
- Test outdated: update with justification in commit message
- Flaky: mark `@flaky`, log for investigation

Never modify a test just to make it pass.

---

## Output — one comprehensive report

Write `docs/testing/test_plan_<phase>_<date>.md`:

```markdown
# Test Plan — <phase> — <date>

## 1. Audit summary (Phase 1)

### Baseline
- Existing tests: <N>
- Passing: <N>/<N> (<%>)
- Coverage: line <%>, branch <%>
- Runtime: <time>

### Coverage by module
| Module | Line | Branch | Tests | Assessment |
|--------|------|--------|-------|------------|

### Qualitative findings
- ✅ good: <modules>
- ⚠️ gaps: <modules with issue>
- ❌ insufficient: <modules>
- Test smells found: <count> (listed below)
- Broken/misleading tests: <count>

### Layer gap analysis
<table with Existing / Expected / Status per layer>

## 2. Completion plan (Phase 2)

### Stream A — Fixes
<table of tests to fix>

### Stream B — Expansion (unit + integration)
<new tests to add in existing layers>

### Stream C — New layers
- Security: <N> tests
- E2E: <N> flows
- UX/UI visual: <N> checks
- Performance: <N> checks (if V1+)

Total new tests: <N>
Projected runtime after completion: <time>

## 3. Execution results (Phase 3)

### Summary
- Status: ✅ PASS / ❌ FAIL
- Total tests: <N> (was <N>, added <N>)
- Passed: <N> (<%>)
- Failed: <N>
- Runtime: <actual> (budget: <planned>)

### Per-layer results
<same structure as baseline, now with new layers>

### Failures detail
<per failure: name, file, expected vs actual, screenshot, suspected cause>

### Coverage after completion
- Line: <%> (was <%>, +<%>)
- Branch: <%> (was <%>, +<%>)

## Recommendations
<anything Claude Code noticed that the human should know before moving on>
```

## Log in SESSIONS.md

```markdown
### Test plan run — <date> — <phase>
- Audit: <N> tests existing, <%> coverage
- Added: <N> new tests (fixed <N>, expanded <N>, new layers <N>)
- Runtime: <X>m (budget: 20m)
- Status: ✅ pass / ❌ fail
- Layers: unit ✅, integration ✅, security ✅, E2E ✅, visual ✅, perf ✅
- Coverage: line <%>, branch <%>
- Report: docs/testing/test_plan_<phase>_<date>.md
- Next: /how-to-navigate (if pass) / /debug (if fail)
```

## Report to human

### If all tests passed

```
✅ Test plan complete — <phase>

Phase 1 (audit):
  Existing tests:   <N>
  Coverage:         <%>
  Gaps found:       <N>
  Smells flagged:   <N>

Phase 2 (completion):
  Fixed:            <N> tests
  Expanded:         <N> new tests in existing layers
  New layers built: security (<N>), E2E (<N>), UX/UI (<N>), performance (<N>)
  Total added:      <N>

Phase 3 (execution):
  Runtime: <X>m <Y>s (budget: 20m)
  All layers: ✅
  Coverage after: line <%>, branch <%>

Report: docs/testing/test_plan_<phase>_<date>.md

Next action: /how-to-navigate
  This will prepare you for exploratory testing — system startup,
  credentials, and a step-by-step navigation plan.
```

### If tests failed

```
❌ Test plan failed at Phase 3 — <phase>

Runtime: <X>m (stopped at layer <L>)
Blockers:
1. <layer>: <failure> — probable cause: <guess>
2. <layer>: <failure> — probable cause: <guess>

Recommendation: Fix before proceeding.
Run /debug <failure 1> to analyze the most critical.
Once blockers are resolved, re-run /test-plan.
```

---

## What this command does NOT do

- Does NOT replace manual human testing — that's `/how-to-navigate` + `/report-bug`
- Does NOT auto-fix failures — the human approves root-cause fixes
- Does NOT change any production code during the audit phase (only adds tests)
- Does NOT delete existing tests without explicit justification in the report
