# /handover

Execute **Step 13 — Handover & Gates**. Generate everything the machine needs to build the
project autonomously: the classic handover artifacts, **the merge-time enforcement layer as
files**, and the ops-pack. Runs **after `/generate-issues` (Step 12)**, before
`/bootstrap-github` (Step 14).

> **Owner:** AI. The edit-time hooks are already wired in `.claude/` from `/new-project`. This
> step adds the **merge-time** half of Tier 3 (CI + CODEOWNERS) and the operability layer, so a
> fresh clone of the repo is protected by versioned files — not by anything on the operator's
> machine.

## Preconditions
- `.vector/issues.json` + `docs/GITHUB_ISSUES.md` exist and are consistent (Step 12 done).
- The design is frozen (`POLICY.md`, `CONTEXT.md`, `design-freeze/v1`).
- The `<plugin>` path is the installed VECTOR plugin root (templates live under `<plugin>/src/`).

## What you do

### 1. Classic handover artifacts
- `CLAUDE.md` — the builder/reviewer's law: stack, architecture patterns (mandatory/forbidden),
  layering rules, naming, how to run tests. Derived from `CONTEXT.md`; this is what every fresh
  process reads first.
- `SESSIONS.md` — skeleton (the deterministic per-merge log the runner appends to).
- `.env.example` — every variable the app needs, no secrets. Real `.env` stays out of git.
- `docker-compose.yml` + **`docker-compose.test.yml`** (hermetic: app + DB, no host coupling —
  this is what `ci-tests`/`conformance` boot).
- `Makefile` — `make dev`, `make test`, `make seed`.
- **Deterministic seed spec** — one account per role + the fixtures the mock and the Explorer
  assume. Same seed every run.

### 2. Enforcement layer — the merge-time gates as files
Copy from the installed plugin and **adapt to this project's stack** (the templates are the
`webapp` reference stack; a `service-api` or other-stack project edits them — do not ship
verbatim):

```bash
mkdir -p .github/workflows .github/scripts
# The two logic nets (real code, red-teamed in the plugin) — copied verbatim, they are stack-agnostic:
cp <plugin>/src/orchestration/ci/coverage_ratchet.py   .github/scripts/
cp <plugin>/src/orchestration/ci/test_protection_ci.py .github/scripts/
# The workflows (webapp reference — ADAPT stack specifics; drop frontend steps for service-api):
cp <plugin>/src/templates/workflows/*.yml .github/workflows/
```

- **Adapt** each workflow to the real stack (package manager, test commands, service containers).
  Keep each **job name === the required-check name** (`ci-tests`, `conformance`, `security`,
  `coverage-ratchet`, `test-protection`) — `/bootstrap-github` requires them by that exact name.
- **`conformance.yml` has one project-provided step:** the migrations↔ERD diff has no universal
  tool, so the template calls `.github/scripts/erd_diff.sh` and fails loudly if it is absent.
  Wire it to this project's stack (e.g. `alembic upgrade head` on a scratch DB → dump the schema
  → diff against `docs/erd.dbml`). Do not delete the step to make the check pass.
- **`CODEOWNERS`** — copy `<plugin>/src/templates/CODEOWNERS`, replace `{{HUMAN_GITHUB_USER}}`
  with the human's GitHub handle. It covers the frozen paths + `POLICY.md` and **not** `tests/**`.
- **Initialize the coverage baseline** so `coverage-ratchet` has something to ratchet against:
  ```bash
  pytest backend/tests --cov=backend --cov-report=xml -q || true
  python3 .github/scripts/coverage_ratchet.py --coverage-xml coverage.xml \
    --baseline .vector/coverage-baseline --set-baseline
  ```
  (For an empty MVP suite the baseline starts at whatever the initial coverage is; it only ever
  ratchets up.)

> `reviewer-approval` is **not** a workflow — it is a status check set by `/review-pr` / the
> relay-runner via the bot identity. `/bootstrap-github` still requires it in branch protection.

### 3. The ops-pack (operability is build-time — Step 19)
Generate the deterministic-ops scaffolding so production is bind-not-build later:
- Health endpoint(s) (`/health`) wired in the app.
- **Structured JSON logs with user-generated-content fields tagged at schema level**, plus a
  **sanitizer module** that strips/hashes those UGC fields (Tier L / Tier C only ever see the
  sanitized stream — see `docs/OPERATIONS.md`).
- `ops/rules.yaml` — all Tier-D thresholds (uptime, disk, cert, backup, error-rate).
- Error-tracker SDK wired (Sentry) — config only.
- Backup cron (daily `pg_dump` → object storage, 30-day retention) + a restore script.
- `MAINTENANCE.md` — the degradation runbook skeleton (maintenance banner + read-only).
- `.vector/ops-journal.md` — one line per event, from the first deploy.

### 4. State & escalation skeletons
- `ESCALATIONS.md` (the human mirror of `.vector/` escalations).
- `.vector/` skeletons: `state.json` is **not** created here (the runner writes it on first
  `/run-phase`); `issues.json` already exists from Step 12.

### 5. Self-check
```bash
test -f CLAUDE.md && test -f docker-compose.test.yml && test -f CODEOWNERS || echo "MISSING core handover file"
ls .github/workflows/*.yml && ls .github/scripts/coverage_ratchet.py .github/scripts/test_protection_ci.py
grep -L '{{HUMAN_GITHUB_USER}}' CODEOWNERS >/dev/null || echo "CODEOWNERS still has an unreplaced placeholder"
python3 -c "import glob,sys; req={'ci-tests','conformance','security','coverage-ratchet','test-protection'}; \
import re; names={re.search(r'^name:\s*(\S+)',open(f).read(),re.M).group(1) for f in glob.glob('.github/workflows/*.yml')}; \
missing=req-names; print('workflow check names:',sorted(names)); assert not missing, ('missing workflows: %s'%missing)"
```

### 6. Report to the human
List what was generated, and flag anything the human must supply before Step 14: the machine
user (for autonomous merges) and any real secrets in `.env`. Then: `/bootstrap-github`.

## Hard rules
- The enforcement layer is **files in the repo**, never operator-side config. A fresh clone must
  be protected.
- Do not weaken a template to make it pass locally. If a check cannot run yet (no app), it is a
  Step-15 preflight finding, not a reason to delete the check.
- Templates are the reference stack. Adapt them honestly; do not present adapted-away pieces as
  still enforced.
