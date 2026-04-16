# /how-to-navigate

Prepare the human for exploratory testing. Claude Code explains how to configure and start the system, then produces a straightforward step-by-step navigation plan tailored to what was built this phase.

Run after `/test-plan` has passed all automated layers. This is the bridge from "Claude Code's testing" to "human's testing."

## Before you start

Read:
- CLAUDE.md, CONTEXT.md, SESSIONS.md
- docs/testing/test_plan_<phase>_<date>.md (the latest test report)
- docs/PRD.md (user workflows)
- docs/views.md (views in scope this phase)
- Recent PRs merged this phase (what was actually built vs. what's stable)

## Execution

### Step 1 — Pre-flight checks

```bash
docker info > /dev/null 2>&1 || echo "⚠️ Docker is not running"
test -f .env || echo "⚠️ .env file missing — copy from .env.example"

# Check required ports are free
for port in 5432 8000 5173; do
  lsof -i :$port > /dev/null 2>&1 && echo "⚠️ Port $port is in use"
done
```

Flag anything that would block startup.

### Step 2 — Inspect the current .env vs .env.example

```bash
# What vars are required?
cat .env.example

# What vars are set?
cat .env 2>/dev/null

# Diff to find placeholders still present
diff <(grep -oE '^[A-Z_]+=' .env.example | sort) <(grep -oE '^[A-Z_]+=' .env 2>/dev/null | sort)
```

Identify which env vars:
- Are missing from .env entirely
- Still contain placeholder values (e.g., `your-api-key-here`, `changeme`, `xxx`)
- Are set but reference unused integrations

### Step 3 — Identify test credentials

Read `backend/scripts/seed.py` (or equivalent) to extract what users are seeded.

Identify per-role test accounts:
- email
- password
- permissions scope
- any pre-seeded data associated with that user

### Step 4 — Build the navigation plan

Based on:
- What primary workflows the PRD defines
- What issues were completed this phase (from SESSIONS.md)
- What test failures were found and fixed during `/test-plan`
- What code was touched recently

Construct a phase-specific navigation plan with four rounds:
1. Happy paths per role
2. Edge cases
3. Views flagged for special attention (based on recent changes)
4. Responsive check

---

## Output — a single human-readable brief

Present everything in chat. Do NOT write a file — this is operational, not durable.

````markdown
🧭 How to navigate — <phase> testing

## 1. Setup

### Config changes needed

<If .env is fully configured:>
✅ Your .env is already configured. No changes needed.

<If placeholders remain:>
Update these values in your `.env` file:
- `<VAR_NAME>` — <what it should be, e.g., "your OpenAI API key">
- `<VAR_NAME>` — <what it should be>

<If .env is missing entirely:>
Create .env from template:
```bash
cp .env.example .env
```
Then fill in these values:
- `<VAR_NAME>` — <what it should be>

### Start the system

```bash
docker compose up -d --build
sleep 10  # wait for services
docker compose exec backend alembic upgrade head
docker compose exec backend python -m backend.scripts.seed
```

### Verify it's up

```bash
curl -s http://localhost:8000/docs > /dev/null && echo "✓ Backend"
curl -s http://localhost:5173 > /dev/null && echo "✓ Frontend"
```

If anything fails: `docker compose logs <service> --tail=50` and run `/debug`.

## 2. Access

- **Frontend**: http://localhost:5173
- **Backend API docs**: http://localhost:8000/docs

## 3. Test credentials

| Role | Email | Password | What they can do |
|------|-------|----------|------------------|
| Admin | admin@<app>.local | <password> | <scope from PRD> |
| Manager | manager@<app>.local | <password> | <scope from PRD> |
| Analyst | analyst@<app>.local | <password> | <scope from PRD> |

## 4. Navigation plan — 4 rounds

Follow this path. Feel free to deviate if something feels suspicious — deviation is the point of exploratory testing.

### Round 1 — Happy paths per role (20-30 min)

**As Admin:**
1. Login → land on dashboard. Does it feel fast? Do the numbers look right?
2. Navigate to each admin view. Anything visually off?
3. Create a user via the admin panel. Does the flow feel natural? Are error messages clear?
4. Change some config values. Do changes reflect immediately? Can you undo?

**As Manager:**
5. Login → navigate the core workflow: <core action from PRD>
6. Complete the primary loop end-to-end: <step A> → <step B> → <step C>
7. Try "cancel halfway" — does state recover cleanly?

**As Analyst:**
8. Login → access what your role is supposed to see
9. Try to access what your role should NOT see. Is the UX clear about permissions?

### Round 2 — Edge cases (15-20 min)

Pay attention to:
- **Empty states**: What does the app look like with no data?
- **Error states**: Submit invalid forms. Are messages helpful?
- **Loading states**: On slow connections (DevTools → Slow 3G), does the UI degrade gracefully?
- **Refresh mid-flow**: Start an action, refresh, does state survive?
- **Browser back/forward**: Does navigation break anything?
- **Session expiry**: Leave the tab 15 min, come back — graceful handling?

### Round 3 — Views that deserve extra attention this phase

<Based on code changes merged this phase:>
- **<view 1>**: <why — recent complex change, known edge case, newly added feature>
- **<view 2>**: <why>
- **<view 3>**: <why>

### Round 4 — Responsive check (10 min)

Open DevTools → mobile viewport (375px):
- Navigation works?
- Any text overflow?
- Modals usable?
- Touch targets big enough (≥44px)?

Repeat at tablet (768px) for 2-3 critical views.

## 5. Things I'd specifically double-check

<Claude Code flags concerns based on code inspection and test results:>
- <concern 1 — e.g., "the optimizer cascade touches portfolio cache; try approving two cases in quick succession">
- <concern 2 — e.g., "BUG-007 from last session was fixed; verify it stays fixed">
- <concern 3>

## 6. Reporting what you find

When you find something, run:
```
/report-bug
```

Claude Code will ask you for the structured details. Or use quick mode:
```
/report-bug -q "Reports table sort is reversed on first load" P2 V03
```

When you're done exploring (or hit a natural stopping point), run:
```
/fix-bugs
```

Claude Code will analyze, prioritize, propose a fix plan, and — after your review — execute it with regression tests.

## 7. Phase acceptance criteria

Your testing is done when:
- [ ] 0 P0 bugs open
- [ ] 0 P1 bugs open (or explicitly deferred with justification)
- [ ] /test-plan passes again with zero regressions from your fixes
- [ ] You've tested all primary workflows at least once per role
````

### Adaptive detail

The plan length should scale with phase scope:
- **MVP close**: 4 rounds, ~60-80 min total
- **V1 close**: 4 rounds + extra attention on new features, ~90-120 min total
- **V2 close**: 4 rounds + regression focus on V1 features, ~90 min total

If the phase was small (single feature, hotfix), produce a shorter brief with only the relevant rounds.

### If the system won't start

Do NOT just report failure. Debug it:
1. Read container logs
2. Check .env vs .env.example for missing vars
3. Check port conflicts
4. Check if migrations are needed
5. Fix what you can automatically, report what needs human action

Only hand over to exploratory testing when the system is genuinely up.
