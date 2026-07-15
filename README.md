# VECTOR

**Visual Engineering and Coding Technique for Outcome-driven Releases**

A structured method for taking what you have in your head to an application running in production — directly, efficiently, unequivocally, robustly. Humans design; the machine builds; deterministic gates keep both honest.

---

## What it is

VECTOR 2.0 is a 19-step process organized in three acts:

- **Act I — Design** (Steps 1–15, human directs, AI assists): sketches → PRD + structured clarify → wireframes → views → API–frontend reference → ERD → OpenAPI → model specs → **interactive mock** (you use the fake app before freezing the real one) → roadmap → **design freeze** (CONTEXT + POLICY, the contract) → issues + machine ledger → handover + enforcement layer → GitHub bootstrap + branch protection → preflight + launch authorization
- **Act II — Build** (Steps 16–17, machine): the autonomous build loop and the autonomous phase close, repeated per phase MVP → V1 → V2
- **Act III — Production** (Steps 18–19, shared): release via `/promote` (staging → smoke → human GO → prod → rehearsed rollback) and operate & evolve — the frozen spec governs the application in production, forever

Five human gates: views ◆ mock ◆ freeze ◆ launch ◆ GO. Everything else is either a derivation from the frozen spec or an escalation.

The core rule is unchanged from v1, now enforced instead of trusted: **the spec is not an input to a supervised agent — it is a contract.** Hooks, CODEOWNERS and CI make violating it mechanically impossible; when the spec is ambiguous, the machine escalates. It never guesses.

---

## The autonomy dial

Set per project in `POLICY.md`; raised only by the human, never by the loop.

| Level | Behavior |
|---|---|
| L0 | Classic v1: human reviews and merges every PR |
| L1 | Human merges; gates live; reviewer runs in shadow (divergence vs. you = trust telemetry) |
| L2 | Autonomous merges + mandatory daily digest with revert authority + one `/how-to-navigate` per phase |
| L3 | Full autonomy: escalations and phase reports only |

---

## What makes v2 different

- **Enforcement as files, not instructions:** PreToolUse hooks (red-teamed, 47-case battery), CODEOWNERS on frozen paths, CI checks (conformance, security, coverage-ratchet, test-protection), branch protection under a dedicated machine user.
- **The interactive mock (Step 9):** a clickable prototype generated from your specs, used before the freeze — the intent check moved to where corrections cost minutes.
- **Escalation as the only ambiguity resolution:** six classes, park-and-continue scheduling, circuit breakers, kill-safe state.
- **Rollback as mechanism:** an annotated tag per autonomous merge; `vector-revert` opens a revert PR through the same gates.
- **Production on the ops cost ladder:** deterministic rules → optional guardrailed local LLM → Claude only when the human invokes it. No resident agents burning tokens watching deploys.
- **Exit guarantee:** every project is a standard repository any team can take over without VECTOR existing.

---

## Stack & profiles

The **`webapp`** profile (complete in 2.0.0) targets the reference stack: Python + FastAPI · React + Tailwind · PostgreSQL · Docker. The **`service/api`** profile is defined as a strict subset (no views/mock; API-level exploration). `cli/library` and `quant-pipeline` arrive in 2.x. Deploy profiles: `vps-compose` (reference) and `aws`.

---

## Requirements

- Claude Code (subscription or API)
- Python 3.11+ (the hooks; later the Tier-2 runner), Node.js, Playwright (the Explorer)
- A GitHub account **plus a dedicated machine user** for autonomous merges

Claude.ai is no longer required: v2's canonical surface is Claude Code end to end. Chat surfaces remain a fine place to think — nothing is real until it is a committed file.

---

## Installation — two layers

### 1. The method on your machine (once)

```
/plugin marketplace add fedeglan/vector
/plugin install vector
```

Installs the namespaced commands (`/vector:new-project`, `/vector:run-phase`, …) and agents globally, versioned as a unit. Manual fallback: clone + `make install`.

> **What works today (2.0.0):** Act I end to end, Tier 3 (the gates — hooks, CI, protection), and the Act III definition. **The Tier-2 relay-runner is not yet shipped** — it is the Phase B deliverable, and what ships now is its build contract plus its executable specification (`tests/fsm_sim.py`, 8/8 scenarios). Until it lands, Act II runs at L0/L1 the v1 way: you drive `/ship-issue` and merge. See *Method status*.

### 2. The contract in each repo

```
/vector:new-project /path/to/projects/my-app
```

The plugin gives you the verbs; each project gets the contract and gates as files in its own repository — hooks, CODEOWNERS, workflows, `POLICY.md`. **The plugin installs the method; the repo instantiates the contract.**

---

## Usage

```
/vector:new-project …      # scaffold
# Steps 1–15: design, mock, freeze, preflight — you direct
/vector:run-phase           # Act II: the machine builds; escalations reach you
/vector:promote             # Act III: staging → smoke → your GO → production
/vector:change-scope        # the only way specs change after the freeze
```

---

## Repository structure

```
vector/
├── .claude-plugin/
│   ├── plugin.json             ← the plugin manifest (this is what /plugin install reads)
│   └── marketplace.json        ← the repo doubles as its own marketplace
├── src/
│   ├── commands/               ← the method's verbs (~20 .md files)
│   ├── agents/                 ← vector-builder · vector-reviewer (model-pinned, isolated context)
│   ├── templates/
│   │   └── POLICY_TEMPLATE.md  ← the per-project autonomy contract
│   └── orchestration/
│       ├── SPEC.md             ← the three-tier Act II spec
│       ├── hooks/              ← the Tier-3 gate hooks + their red-team batteries
│       │   ├── frozen_specs.py · test_protection.py · deps_guard.py
│       │   ├── hooks.json      ← the settings wiring copied into each project
│       │   └── tests/          ← redteam.py · redteam2.py (47 cases; a project's own gate suite)
│       └── runner/             ← the Tier-2 relay-runner
│           ├── README.md       ← the build contract + CLI
│           └── tests/fsm_sim.py  ← the executable spec of the control flow (8/8)
├── docs/
│   ├── VECTOR.md               ← the full v2 method (19 steps)
│   ├── OPERATIONS.md           ← the Step-19 ops spec (cost ladder, migrations, solo-ops)
│   └── DECISIONS.md            ← decisions, council audits, validation, rollout
├── CHANGELOG.md                ← method versioning (semver)
├── Makefile                    ← install fallback + `make test` (runs the gate batteries)
├── README.md
└── LICENSE
```

---

## Commands

| Command | What it does |
|---|---|
| **Setup** | |
| `/setup` | Install the runner + Playwright, authenticate GitHub, guide the machine-user token, and prove the gates hold on this machine |
| `/new-project` | Scaffold a project: structure, hooks wired, GitHub repo. Instantiates the contract side |
| `/resume` | Detect where a project stands (runner state is authoritative in Act II) and continue |
| **Act I — Design** | |
| `/design` | The Act I driver: sketches → PRD → wireframes → views ◆ → reference → ERD → OpenAPI → model specs → roadmap |
| `/clarify` | Structured coverage interrogation of the PRD; `[NEEDS CLARIFICATION]` markers |
| `/mock` | Generate the Step-9 interactive prototype from the frozen-track artifacts ◆ |
| `/freeze-design` | CONTEXT + POLICY + baselines + tag — the contract ◆ |
| `/bootstrap-github` | Board, labels, milestones, DEV branch, branch protection, machine-user verification |
| `/preflight-audit` | Ambiguity scan · coverage matrix · env dry-run · hooks red-team + revert rehearsal ◆ |
| **Act II — Build** | |
| `/run-phase` | The dispatcher: launch and monitor the autonomous loop for a phase |
| `/ship-issue` | The per-issue pipeline: branch → implement → review → gates → merge → tag |
| `/solve-issue` | Implement a specific issue with debugging guidance |
| `/review-pr` | Review a PR against the specs; sets the `reviewer-approval` status check |
| `/explain-pr` | Explain a PR in very simple terms |
| `/audit-plan` | Audit the codebase against the plan and specs (drift check + phase gate) |
| `/test-plan` | Complete and run the suite; classify every failure (code-bug / test-bug / flaky / spec-conflict) |
| `/explore` | The Playwright Explorer: network-asserted walkthroughs + visual regression |
| `/debug` | Analyze and fix broken things |
| `/fix-bugs` | Work the backlog by severity; every fix ships a regression test through the full gates |
| `/escalate` | File a decision request; park-and-continue. The only sanctioned answer to ambiguity |
| `/change-scope` | The only way a frozen spec changes — with impact analysis and human approval |
| **Act III — Production** | |
| `/promote` | Staging → Explorer smoke → human GO ◆ → prod → verify → rollback |
| `/triage` | The morning ops session over the sanitized digest |
| **Human tools** | |
| `/how-to-navigate` | Prepare the human for exploratory testing (required once per phase at L2) |
| `/report-bug` | Capture a bug during exploratory testing |
| `/upgrade-project` | Retrofit a VECTOR v1 repo to the v2 contract |

◆ = a human gate.

---

## Method status

**v2.0.0 — definition frozen 2026-07-15.** Validated pre-freeze by execution (hooks red-team 47/47 with one real bypass found and fixed; runner state machine 8/8 scenarios including kill/resume identity; consistency audit resolved) and by two council audits. Implementation rolls out in gated phases A–F — see `docs/DECISIONS.md`. The published 15-step method is anchored at the `v1-final` git tag. Changes to the method itself now go through its own change-scope discipline.

---

## License

MIT

## Citation
Glancszpigel, Federico M., VECTOR: A Structured Method for AI-Assisted Fullstack Software Development (April 03, 2026). Available at SSRN: https://ssrn.com/abstract=6516343
