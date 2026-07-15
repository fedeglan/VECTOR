# CI workflow templates — the merge-time half of Tier 3

> **These are `webapp` reference-stack templates** (Python + FastAPI + PostgreSQL · React +
> Tailwind), **not universal.** `/vector:handover` (Step 13) copies them into a project's
> `.github/workflows/` and **adapts** the stack specifics (package manager, test commands,
> service containers) to what the project actually uses. A `service-api` project drops the
> frontend steps; a different stack rewrites the install/test lines. Do not ship them verbatim
> to a non-reference stack.

## The six required checks (POLICY §6)

Branch protection on `DEV` requires all six. Five are workflows here; the sixth is set by the
reviewer, not a workflow.

| Check | Where it lives | What it enforces |
|---|---|---|
| `ci-tests` | `ci-tests.yml` | the test pyramid (backend + frontend) passes |
| `conformance` | `conformance.yml` | endpoints ↔ `docs/api-spec.yaml` (schemathesis); migrations ↔ `docs/erd.dbml`; architecture rules (import-linter) |
| `security` | `security.yml` | gitleaks + bandit + pip-audit / npm audit |
| `coverage-ratchet` | `coverage-ratchet.yml` → `.github/scripts/coverage_ratchet.py` | coverage may never drop (the net for neutered tests) |
| `test-protection` | `test-protection.yml` → `.github/scripts/test_protection_ci.py` | diff-based deletion/skip/weakening detector requiring a signed justification block |
| `reviewer-approval` | **not a workflow** | a status check set by `/review-pr` / the relay-runner via the bot identity |

## The two logic nets (not YAML — executable, with their own red-team battery)

`coverage-ratchet` and `test-protection` are the named downstream nets for the edit-time
hooks' documented residuals (whole-file test overwrites, early-return neutering, mv-rename-out).
They are real Python in `src/orchestration/ci/` — `coverage_ratchet.py`, `test_protection_ci.py`
— with an executed battery (`src/orchestration/ci/tests/redteam_ci.py`, 18/18, run by
`make test`). `/handover` copies both scripts into the project's `.github/scripts/`. This is
what makes "defense in depth is a verified property, not rhetoric" (SPEC §3.1) true.

## Job names == check names

Each workflow's job name is the exact required-check name so `/bootstrap-github` (Step 14)
can require it in branch protection. Renaming a job renames the check — keep them in sync.
