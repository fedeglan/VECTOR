# VECTOR — The Method (v2.0.0)

> **Definition frozen 2026-07-15.** From this version onward, changes to the method go through its own change-scope discipline: a proposed amendment, an impact assessment, a version bump. Supersedes the published 15-step v1.
>
> **North Star:** take what the user has in their head to a concrete production application — directly, efficiently, unequivocally, robustly.
>
> **Canonical surface:** Claude Code, end to end. claude.ai (or any chat surface) is a non-canonical ideation vestibule; nothing is real until it is a committed file. The process starts at `/vector:new-project`.

**Scope & profiles.** VECTOR targets any software development project through **project profiles**. v2.0.0 ships the **`webapp`** profile complete — the 19 steps below as written — and defines **`service/api`** as a strict subset (see *Profiles*). Further profiles (`cli/library`, `quant-pipeline`) arrive in 2.x minors. Primary user: the method's author and his projects; open-source adoption is a deliberate by-product. The human retains legal and compliance responsibility — the method generates a launch checklist; it owns none of it. No brownfield yet, except `/upgrade-project` for VECTOR v1 repositories. **Exit guarantee:** every project is a standard repository (gitflow, tests, CI, docs) that any team can take over without VECTOR existing.

**Installation — two layers.**
1. **The method on your machine** (once): `/plugin marketplace add fedeglan/vector` → `/plugin install vector`. Installs the namespaced commands (`/vector:new-project`, `/vector:freeze-design`, `/vector:run-phase`, …) and the agents globally, versioned as a unit — updating the method is an explicit plugin action, never silent. Manual fallback: clone + `make install` (copies `commands/` and `agents/` to `~/.claude/`). The Tier-2 runner installs separately (`pipx install`, ships with the orchestration layer).
2. **The contract in each repo** (`/vector:new-project`): the plugin gives you the *verbs*; each project needs the *contract and gates as files in its repository* — hooks wired in the project's `.claude/settings.json`, CODEOWNERS, CI workflows, `POLICY.md` — because Tier 3 is repo-native by design: a plugin can enforce nothing; versioned files plus branch protection can. **The plugin installs the method; the repo instantiates the contract.**

Entry ritual — `/vector:new-project`: creates the repo skeleton, the project-level `.claude/` (settings with hook wiring, agent overrides), gitignore/LICENSE, and the folder structure. One command; everything below assumes it ran.

---

## Act I — Design (human directs, AI assists; Steps 1–15)

Human judgment is front-loaded here. Everything downstream is either derivation from what this act freezes, or an escalation.

**Driver:** `/vector:design` conducts this act — the counterpart of `/vector:run-phase` in Act II. Steps with their own command are named below; the rest run under `/design`.

### Step 1 — Sketches
**Owner:** human. **Inputs:** the idea. **Activities:** hand-draw screens and flows; photograph; drop into `docs/sketches/`. Ideation conversation may happen anywhere (the chat vestibule), but the artifacts land in the repo. **Outputs:** `docs/sketches/*`. **Exit:** enough raw material to interrogate.

### Step 2 — PRD + Clarify
**Owner:** both. **Inputs:** sketches + conversation. **Activities:** draft the PRD — problem, roles/personas, user stories per role, in/out of scope. Then `/clarify`: structured, coverage-based interrogation (functional scope, roles and permissions, data lifecycle, edge cases, integrations, non-functionals), ≤5 questions per round, answers recorded in a dated **Clarifications** section. Anything unresolved is marked **`[NEEDS CLARIFICATION]`** inline — the marker convention is born here and governs every artifact from now on: unresolved intent is *visible*, never silently interpreted. **Outputs:** `docs/PRD.md` (frozen-track). **Exit:** PRD stable; live markers may remain (they are executed at Step 15, where zero-live-markers is a launch condition).

### Step 3 — Wireframes
**Owner:** both. **Inputs:** PRD stories. **Activities:** low-fidelity structure per view — layout blocks, navigation, and the three states (empty / loading / error) per view. **Outputs:** `docs/wireframes/*`. **Exit:** every user story has its views.

### Step 4 — Views ◆
**Owner:** both. **Inputs:** wireframes + aesthetic direction. **Activities:** define the aesthetic (palette, typography, density); render each view at high fidelity; render **locally, file → real browser** (Claude in Chrome is fine here — this is interactive human use); iterate; log approval per view in `views.md`. **Outputs:** `docs/views.md` + the approved renders — **these exact renders become `baselines/` at the freeze and are the Explorer's visual oracle**, which is why they must be produced in the same pipeline that will later screenshot them. **Gate ◆:** visual fidelity approved.

### Step 5 — API–Frontend Reference
**Owner:** both. **Inputs:** views + PRD. **Activities:** for every view, an action table: element → event → endpoint (method + path) → payload → expected UI result. **YAML is the source of truth** (`docs/api-frontend-reference.yaml`); the `.docx` is rendered from it. **Exit:** every interactive element mapped; unknown endpoints carry markers.

### Step 6 — ERD
**Owner:** both. **Inputs:** PRD + reference. **Activities:** entities, relations, constraints, indexes; point-in-time/audit fields where the domain needs them. **Outputs:** `docs/erd.dbml` (frozen-track).

### Step 7 — OpenAPI
**Owner:** both. **Inputs:** reference + ERD. **Activities:** full `api-spec.yaml` — paths, schemas, auth, RBAC per role, error envelope, pagination conventions — cross-checked against the reference (every mapped endpoint exists; no orphan endpoints). **Outputs:** `docs/api-spec.yaml` (frozen-track).

### Step 8 — Model Specs
**Owner:** both, when the app has quant/ML logic. **Activities:** one MSD per model — objective, inputs and point-in-time rules, method, outputs, validation criteria, failure modes. **Outputs:** `docs/research/msd_*.md` (frozen-track).

### Step 9 — Interactive Mock ◆
**Owner:** both. **Inputs:** views (4) + OpenAPI (7) + reference (5). **Activities:** an agent generates a clickable prototype (e.g. Vite + MSW) wiring every action-table row to mocked responses derived from the OpenAPI schemas and seed-like fixtures. The human **uses the fake application end to end, per role**. **Anti-drift rule:** the mock is *generated* from the frozen-track artifacts and *disposable* — never hand-edited; every divergence discovered while using it is fixed **in the upstream spec** (views / reference / OpenAPI / PRD) and the mock is regenerated. One contract, one oracle. **Timebox:** 2–3 days; if it takes longer, it is being built too well. **Gate ◆:** *"I used the fake app and it is what I had in my head."* This is the intent check moved to where corrections cost minutes instead of change-scopes.

### Step 10 — Roadmap & Phases
**Owner:** both. **Activities:** slice scope into MVP → V1 → V2; each phase a shippable, coherent subset; per-phase coverage of views/endpoints/entities. **Outputs:** `docs/roadmap.md`. **Exit:** every PRD story assigned to a phase.

### Step 11 — Design Freeze ◆
**Owner:** human approves. **Activities:** generate `CONTEXT.md` (module map, conventions, architecture patterns); **instantiate `POLICY.md`** from the template — the human sets: starting `autonomy_level` (the level is the human's sovereign choice; the earned path L1→L2→L3 is the recommended default), budgets, breakers, graduation thresholds, explorer cadence and visual thresholds, notification recipients, the **deploy profile** (`vps-compose` | `aws`), and pins `method_version`; archive the Step-4 renders to `baselines/`; walk the freeze checklist; tag `design-freeze/v1`. **Gate ◆ — THE CONTRACT:** from this commit onward, specs change only via `/change-scope`; downstream ambiguity escalates, never guesses; the escalation rate becomes the design-quality KPI.

### Step 12 — Issues & Ledger
**Owner:** AI generates, human reviews by sampling. **Activities:** `GITHUB_ISSUES.md` — one self-contained issue per unit of work: context, exact task, files, **`verification:` block of executable commands whose exit codes define done**, model label, complexity label, dependencies. DAG sanity (acyclic, phase-consistent). Emit `.vector/issues.json` — the machine ledger the runner consumes. **Exit:** human spot-review; a criterion not expressible as a command or test is incomplete design and goes back upstream, not forward.

### Step 13 — Handover & Gates
**Owner:** AI. **Activities:** the classic handover (`CLAUDE.md`, `SESSIONS.md` skeleton, `.env.example`, `docker-compose.yml` + hermetic `docker-compose.test.yml`, Makefile, deterministic seed spec — accounts per role + fixtures) **plus the entire enforcement layer as files**: `.github/workflows/` (ci-tests: the pyramid; conformance: schemathesis endpoints↔OpenAPI + migrations↔ERD diff + import-linter architecture rules; security: gitleaks + bandit/pip-audit or npm audit; coverage-ratchet; test-protection: diff-based detector of deletions/skips/weakened assertions requiring a signed justification block); `CODEOWNERS` on frozen paths + `POLICY.md`; hooks installed (`frozen_specs`, `test_protection`, `deps_guard`, budget counters, optional notify) with settings deny-rules covering the `@`-reference gap; the **ops-pack** (see Step 19: health endpoints, tagged log schema, sanitizer, `ops/rules.yaml`, backup cron, runbook skeleton); `ESCALATIONS.md` and `.vector/` skeletons.

### Step 14 — Bootstrap & Protection
**Owner:** AI, authenticated as the **machine user**. **Activities:** labels (phase, model, complexity, `needs-human`, `escalated`), milestones per phase, issues pushed, project board (Backlog / In progress / In review / Done), DEV branch, **branch protection with the required checks**, machine-user permission verification, self-verifying asserts against `issues.json` (counts match). **Exit:** GitHub scaffolding live and provably consistent with the ledger.

### Step 15 — Preflight & Launch Authorization ◆
**Owner:** both. Four tracks, all must pass:
1. **Ambiguity scan** — an adversarial, fresh-context agent reads all issues + specs hunting contradictions and non-executable criteria; **zero live `[NEEDS CLARIFICATION]` markers** is a hard condition.
2. **Coverage matrix** — every story ↔ ≥1 endpoint ↔ ≥1 view ↔ ≥1 issue; an orphan in any direction is a finding; output formatted as a checklist ("unit tests for English").
3. **Environment dry-run** — stack boots via compose; empty suite green in CI; `gh` authenticated as machine user; Playwright installed; `POLICY.md` parses fail-fast; notify hook reachable if enabled.
4. **Hooks red-team + revert rehearsal** — the validated battery executed in-repo: an agent provably cannot edit a frozen spec, delete a test, add a dependency silently, or merge past a red check; one `vector-revert` executed successfully.
**Gate ◆ — launch authorization: the last human gate of Act I.**

---

## Act II — Build (machine; Steps 16–17, repeated per phase MVP → V1 → V2)

Three tiers: **Tier 1** — a Claude Code session as thin dispatcher (`/run-phase` + `/goal`; the v1 UX: open, run, watch, intervene). **Tier 2** — the deterministic relay-runner spawning **one fresh `claude -p` process per role per issue** with turn and time limits. **Tier 3** — the gates from Step 13/14, which outrank every model's judgment. The human surface: escalations, plus the digest at L2.

**Billing note (subscription mode):** under a Claude Code subscription there is no marginal token cost; budgets bind through `--max-turns` and time limits, and **subscription rate-limit windows are handled as infra-pauses** — the runner parks until the window resets and resumes from state — never as failures or breaker events. Token usage is still logged per issue for the efficiency ledger.

### Step 16 — Autonomous Build Loop
**Start:** open Claude Code, run `/run-phase`. The dispatcher reads `POLICY.md` + `.vector/state.json` + `issues.json`, sets `/goal` to the phase acceptance condition (a continuation mechanism, never a verifier), and launches/monitors the relay.

**Per-issue pipeline (relay-runner):**
1. Pick the next `queued` issue whose dependencies are all `merged`.
2. **Builder** (fresh process, model per issue label): branch from DEV → implement per the issue's self-contained prompt → run tests + self-check → push → open PR → structured JSON exit.
3. **CI wait:** red → classify (test/build failure → next attempt with the failure log attached, ≤3 attempts total; CI infra failure → retry once, then escalate as `infra`).
4. **Reviewer** (fresh process, model per pairing table; sees diff + issue + specs, never the builder's transcript): full checklist, **mandatory test-delta inspection**, plain-language summary (feeds the digest); verdict sets the required `reviewer-approval` status check.
5. `CHANGES_REQUESTED` → builder fix cycle on the same branch (≤2 cycles; **third rejection escalates with both positions attached**).
6. **Merge:** all required checks green → merge, delete branch, close issue, **annotated tag `vector/T<NNN>I<N>`** (the rollback handle), deterministic `SESSIONS.md` entry, cost/tokens accounted.
7. **Cadence:** every 10 merges → `/audit-plan` (blockers auto-file fix issues) + Explorer smoke (rounds 1+3).

**Dial behavior:** **L1** — reviewer runs in shadow (verdict recorded to `.vector/shadow.json`, compared with the human's decision; divergence = graduation telemetry); the human merges. **L2** — autonomous merges + **mandatory daily digest** (deterministic: merges with reviewer summaries, files, cost, escalations, revert handles; ~20 min; no action required to continue; revert authority applies) + **one required `/how-to-navigate` per phase** (the intent check). **L3** — digest optional (recommended ON for a project's first run). Graduation: L1→L2 at shadow divergence <10% over ≥20 PRs; L2→L3 at revert rate <2% over ≥50 merges + the benchmark. **Levels are raised only by the human, never by the loop.**

**Escalation (the only ambiguity resolution):** `spec-conflict | ambiguity | budget | infra | security | review-deadlock` → entry in `ESCALATIONS.md` with the exact decision needed as a question + `needs-human` label + optional notify. **Park-and-continue:** dependents are blocked, independent DAG branches continue. Freeze-class (halt the phase): critical security finding; spec-conflict blocking >50% of the remaining DAG. Breakers: 3 consecutive terminal failures halt the run; the same test failing after 3 fix attempts escalates; Tier-1 context >50% or compaction → checkpoint + session rotation.

**Human return path:** answer in the issue or inline; spec-conflicts must pass through `/change-scope` (freeze marker updated) before the item re-queues — enforced by timestamp comparison.

**Controls:** type at any moment; halt = Esc or `.vector/HALT` (takes effect at the next issue boundary); resume = restart `/run-phase` — state on disk is authoritative and kill-safe (validated by simulation pre-freeze).

### Step 17 — Autonomous Phase Close
Triggered when every phase issue is `merged` or `escalated`/blocked:
1. `/audit-plan` — blocking; blockers auto-file fix issues → back to the loop.
2. `/test-plan` (fast) — failures classified: **code-bug** → auto `/debug` + fix + mandatory regression test; **test-bug** → fix with justification + reviewer sign-off on the delta; **flaky** → retry ×2 → quarantine + auto-filed issue; **spec-conflict** → escalate, never resolve by choice.
3. `/explore` (full, Playwright): **Round 1** — happy paths per role: walk every row of the api-frontend-reference, **intercept network traffic, assert the exact mapped endpoint + method fired**, assert a sane UI response. **Round 2** — edge battery: empty states, invalid forms, refresh mid-flow, back/forward, session expiry. **Round 3** — views flagged by the phase's merged PRs via the CONTEXT module map. **Round 4** — screenshots at 3 viewports, diff vs `baselines/` per POLICY thresholds, a11y. Every finding → `BUG_BACKLOG.md` in `/report-bug` format, severity by rubric (P0 flow broken · P1 wrong/failed endpoint · P2 state/UX anomaly · P3 visual over threshold), **screenshot + network log attached**.
4. `/fix-bugs` (auto): the matrix executes without an approval gate; P0 one per batch; every fix PR passes the full step-16 gate sequence; deferrals logged with justification.
5. `/test-plan` (thorough) — regressions send it back to 4.
6. **Acceptance:** 0 P0 · 0 P1 or justified deferral · audit clean → phase report → **notify-and-continue** into the next phase. 16↔17 repeat until V2 is done.

---

## Act III — Production (shared; bind, not build)

### Step 18 — Release ◆
Human-invoked `/promote`. **Preconditions:** phase accepted, DEV green. **Pipeline:** deploy to **staging** on the project's **deploy profile** — `vps-compose` (reference implementation: compose + reverse proxy + systemd; staging = separate compose project with synthetic seed) or `aws` (requirements-level; for compute/user scale that demands it) — chosen at Step 11, minimal IaC generated at Step 13 → **Explorer smoke against staging** (the same agent, reused as the release gate) → **◆ human GO — the single production human gate** → deploy to prod → post-deploy verification (health checks + smoke) → rollback path rehearsed (deploy rollback + the `vector-revert` discipline). Release policy lives as a POLICY section.

### Step 19 — Operate & Evolve
**Designed 2026-07-15** — full specification in `docs/OPERATIONS.md`; observation-dependent items are dated calibration points, not gaps. Principles: **bind, not build**, and the **ops cost ladder** — **Tier D** deterministic rules (always on, ~zero cost: uptime probes, threshold alerts, log pattern matchers, supervised restarts, backups) → **Tier L** optional small local LLM (guardrailed: sanitized input only, bounded schema-validated JSON out, no tools, no network; degrades to raw counts) → **Tier C** Claude, **human-invoked only** (`/triage`, postmortems), never resident in production. Attention contract: immediate pages for criticals — the human manages silence on-device — plus a ~30-minute weekday morning triage window as the only scheduled ops attention. Hard requirements built in: **(a) production-injection controls** — UGC tagged at log-schema level, sanitized before any model sees it, raw logs human-eyes-only; **(b) live-data migration discipline** — expand-contract deploys, backfills with resume, rehearsal on anonymized prod snapshots, a migration gate in that change's `/promote`; **(c) honest solo-ops** — degradation defaults (maintenance banner + read-only), no on-call theater. Incidents enter via `/report-bug` into the severity matrix and the existing hotfix path. **Evolve:** intent changes via `/change-scope` — the frozen spec governs the application in production, forever; new features re-enter Act II as a new phase at the project's dial level; dependency updates arrive as deps-guard escalations resolved in a maintenance phase. Exit guarantee holds.

---

## Profiles

A profile marks each step **applicable / N-A / swapped**; a step marked N-A drops out of preflight's coverage matrix automatically.

- **`webapp`** (v2.0.0, complete): all 19 steps as written above.
- **`service/api`** (v2.0.0, defined): a strict subset — Steps 3, 4 and 9 are N-A (no views, no visual baselines, no mock; the intent check moves to contract examples plus a generated API playground the human exercises), Step 5 becomes a consumer↔endpoint mapping, and the Explorer swaps to API-level probing (schemathesis + scenario contract tests against staging). Everything else — freeze, POLICY, issues, gates, autonomous loop, release, operate — is identical.
- **`cli/library`** and **`quant-pipeline`** (MSD-centric): 2.x minors.

## Cross-cutting

**Invariants → enforcement:** (1) specs are law — hooks + CODEOWNERS + conformance CI + `/change-scope` as the only mutation path; (2) builder ≠ reviewer — fresh process per role, reviewer tier ≥ builder; (3) deterministic gates outrank model judgment — branch protection makes merge mechanically impossible otherwise; (4) every fix ships a regression test; (5) tests are protected artifacts — hook at edit time, `test-protection` check at merge time, coverage-ratchet as the net for neutered tests; (6) everything budget-bounded — flags + on-disk counters + breakers; (7) full traceability — JSON-authoritative state, `SESSIONS.md`/`ESCALATIONS.md` as human mirrors.

**Human-time accounting (the North Star ledger):** Act I design work + five gates (views, mock, freeze, launch, GO) · escalations · ~20 min/day of digest while at L2 · one GO per release. Metric tracked from project one: total human-hours head→production and cost per shipped feature; if v2 does not beat v1 by project two or three, the definition failed by its own standard.

**Method versioning:** VECTOR carries semver + `CHANGELOG.md` and ships as a Claude Code plugin — updating the method is an explicit plugin action, never silent; each project pins `method_version` in `POLICY.md` at its freeze. A design frozen against a floating method is not frozen.
