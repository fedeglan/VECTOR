# VECTOR relay-runner (Tier 2)

> Deterministic Python. **Built (Phase B, 2026-07-15)** against the executable
> specification in `tests/fsm_sim.py` (8/8) and `../SPEC.md`. Status below.

## Status — built and battery-proven
The `vector_runner/` package is implemented and installs a real `vector-run` /
`vector-revert` entry point (`pip install -e .`). Its control flow is **executed**, not
asserted:
- `tests/fsm_sim.py` — the original executable control-flow spec, **8/8** (untouched).
- `tests/test_fsm_live.py` — the **same 8 scenarios run against the REAL runner** via
  deterministic `claude`/`gh`/`git` shims (`tests/shims/`), **plus 22 live-behavior
  scenarios** (real `SIGKILL` mid-build + state-only resume, HALT, sticky breaker,
  identity/window/policy fail-fast, never-raise, CI-red budget sharing, change-scope
  requeue, L0/L1 no-merge), **plus 9 red-team regressions** (the `F*` series) — **39/39**.
- The parser reads the real pilot `POLICY.md`; the spawn contract was verified against
  the real `claude` CLI (flags accepted, JSON envelope parsed).
- **Adversarial red-team:** a 7-lens fan-out (16 agents) executed real attacks against
  the runner; **9 confirmed violations were found and fixed** (crash-safe atomic merge,
  per-issue wall budget for reviewer/CI, final-block-only exit parsing, PR-ownership
  verification, fail-fast numeric POLICY, full escalation template, unclean-phase
  refusal). Each is pinned by an `F*` regression in `test_fsm_live.py`.

**Not yet exercised (honest):** a full loop with real `claude -p` *builder/reviewer*
processes closing issues on a live repo — blocked only on (a) an **authenticated
headless CLI** (`claude` in a fresh subprocess reports "Not logged in"; needs
`claude setup-token` or `ANTHROPIC_API_KEY`) and (b) a **dedicated machine user** for
autonomous merges under branch protection. Both are operator credential actions. The
runbook below is turnkey once they exist.

## Live-run runbook (operator)
```bash
# 0. one-time: authenticate the HEADLESS cli + (for L2) a dedicated machine user
claude setup-token            # or: export ANTHROPIC_API_KEY=...   (headless builders need this)
# create a GitHub machine user, gh auth login AS it, set POLICY merge.bot_identity to it

# 1. install the runner
pip install -e src/orchestration/runner

# 2. add a phase slice to the project's .vector/issues.json, e.g. a clean + an ambiguous issue:
#    {"id":"V101I1","phase":"v1","title":"Add GET /health/ready readiness probe (DB SELECT 1 -> 200
#      {ready:true} else 503). Adds backend/tests/test_health.py. Touches no frozen spec.",
#      "model":"sonnet","complexity":"low","deps":[]}
#    {"id":"V101I2","phase":"v1","title":"Replace offset/limit with cursor pagination on GET /links",
#      "note":"INTENTIONALLY UNDERSPECIFIED: no cursor encoding, tiebreaker, or api-spec change given
#      — the correct outcome is a BLOCKED escalation, not a guess","model":"sonnet","deps":[]}

# 3. run the phase (L1 = human merges each PR; L2 = autonomous merges via the machine user)
vector-run --cwd <project> start --phase v1
vector-run --cwd <project> status         # watch it
# kill it any time (Ctrl-C / SIGKILL) and:
vector-run --cwd <project> resume         # resumes from .vector/state.json alone

# expected: V101I1 -> real PR opened under runner control -> reviewer -> (merge or human);
#           V101I2 -> BLOCKED escalation in ESCALATIONS.md (the runner never guesses).
```

## What it is
The relay-runner is the deterministic engine of Act II. It spawns one fresh `claude -p`
process per role per issue, drives the per-issue pipeline, enforces budgets and breakers,
merges through the gates, tags each merge, and persists kill-safe state after every
transition. Its scope is deliberately minimal — dispatch, spawn, poll, merge, tag, log,
digest, revert — so it never competes with what the platform may ship natively.

## CLI
```
vector-run start     [--phase <name>] [--level L0|L1|L2|L3]   # begin/continue a phase
vector-run resume                                             # resume from .vector/state.json
vector-run status                                             # print state summary
vector-run halt                                               # write .vector/HALT (stops at next issue boundary)
vector-revert <tag>                                           # open a revert PR through the same gates
```
`start` reads `POLICY.md` + `.vector/state.json` + `.vector/issues.json`, refuses to run
outside `run_window`, and never raises the autonomy level it reads.

## Package layout (Phase B)
```
runner/
├── pyproject.toml          # installs the vector-run + vector-revert entry points (pipx)
├── vector_runner/
│   ├── __init__.py
│   ├── cli.py              # argparse -> start/resume/status/halt/revert
│   ├── state.py            # .vector/state.json read/write; atomic, after every transition
│   ├── policy.py           # parse POLICY.md fenced-yaml blocks; fail-fast on missing keys
│   ├── scheduler.py        # ready-set (deps merged), park-and-continue, breakers
│   ├── pipeline.py         # the per-issue build->ci->review->fix->merge sequence
│   ├── spawn.py            # claude -p invocation: model pinning, --max-turns, --disallowedTools
│   ├── gates.py            # gh checks polling; reviewer-approval status; merge + tag
│   ├── digest.py           # deterministic daily digest (no LLM call)
│   ├── revert.py           # vector-revert: revert PR through the gates
│   └── notify.py           # optional one-way Telegram
└── tests/
    ├── fsm_sim.py          # THE executable spec of the control flow (ships now, 8/8)
    └── test_*.py           # unit tests added during Phase B
```

## Control-flow spec
The state machine, transition semantics, budget/breaker accounting, shadow-mode
recording, and kill/resume identity are all specified executably in `tests/fsm_sim.py`.
Phase B's job is to make the real runner match it against live `claude -p` processes and
real `gh` calls. Any behavioral question the prose leaves open is answered by running the
simulator.

## Billing modes
`subscription` (default): no marginal token cost; limits bind via `--max-turns` and time
budgets; subscription rate-limit windows are handled as **infra-pauses** — park until the
window resets, resume from state, never a failure or breaker event. `api`: optional USD
caps apply. Tokens + wall-time are logged per issue either way (the efficiency ledger).
