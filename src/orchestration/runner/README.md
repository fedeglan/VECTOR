# VECTOR relay-runner (Tier 2)

> Deterministic Python. Built in **Phase B** against the executable specification in
> `tests/fsm_sim.py` (validated pre-freeze, 8/8 scenarios). This README is the build
> contract; the full behavioral spec is `../SPEC.md`.

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
