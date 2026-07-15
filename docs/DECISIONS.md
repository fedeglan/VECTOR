# VECTOR v2 — Design Decisions & Rollout Plan

> The architecture record behind v2.0.0: what was decided, what two council audits
> amended, what executable validation found, and how the rollout is gated.
> Definition frozen 2026-07-15; changes to the method now go through its own
> change-scope discipline. The method itself: `docs/VECTOR.md`. Act II mechanics:
> `src/orchestration/SPEC.md`. Ops: `docs/OPERATIONS.md`.

**North Star:** take what the user has in their head to a concrete production
application — directly, efficiently, unequivocally, robustly. Humans do design, launch
authorization, and escalations; the machine does the hours; deterministic gates keep
both honest.

## 1. Decision record (consolidated at freeze)

| Area | Decision |
|---|---|
| Execution host | Headless on the author's always-on Mac; Claude Code end-to-end is the canonical surface — chat surfaces are a non-canonical ideation vestibule (nothing is real until committed) |
| Architecture | Three tiers: session dispatcher (`/run-phase` + `/goal`) / deterministic Python relay-runner (fresh `claude -p` per role per issue) / repo-native gates. GitHub Actions carry deterministic checks only |
| Autonomy | Dial L0–L3 in POLICY; graduation is data-earned and human-only (shadow divergence <10% over ≥20 PRs → L2; revert rate <2% over ≥50 merges + benchmark → L3). Author's personal starting default: L3 with digest ON |
| Budgets & breakers | 3 build attempts (CI-red retries share the budget) · 2 review cycles · 60 min/issue · 8 h/run · 3 consecutive terminal failures halt (issue-level counting; only budget-class failures feed the breaker) · same test 3 fix attempts escalates |
| Billing | Subscription mode: no marginal token cost; limits bind via turns/time; rate-limit windows = infra-pauses (park + resume), never failures |
| Merge policy | DEV is the autonomous terminal; main/deploy human-only via `/promote`. Required checks: ci-tests, conformance, security, coverage-ratchet, test-protection, reviewer-approval. Dedicated machine user. Annotated tag per merge + scripted `vector-revert` through the same gates |
| Review | Reviewer tier ≥ builder (Haiku→Sonnet, Sonnet→Opus, complexity:high→Opus); full checklist always; mandatory test-delta inspection; fresh context, never the builder's transcript |
| Testing & QA | Test-protection as hard block (hook + CI + ratchet); Explorer = Playwright with network-level endpoint assertions (Claude in Chrome reversed on evidence — interactive prompts, no clean interception; stays human-only via `/how-to-navigate`, mandatory once per phase at L2); smoke every 10 merges, full 4 rounds at phase close; visual: MVP functional-only, V1+ ≥2% area = P3 |
| Specs as law | `api-frontend-reference.yaml` as source of truth; executable `verification:` blocks per issue; `issues.json` machine ledger; `[NEEDS CLARIFICATION]` markers born at the PRD, executed at preflight |
| Contract | POLICY.md instantiated per project at freeze; `method_version` pinned; VECTOR itself semver'd and shipped as a Claude Code plugin (the plugin installs the method; the repo instantiates the contract) |
| Scope | Project-agnostic via **profiles**: `webapp` complete in 2.0.0, `service-api` defined as strict subset, `cli/library` + `quant-pipeline` in 2.x. No single anointed live project — Phase A runs on the first pilot; the synthetic benchmark regains weight accordingly |
| Naming & paper | The method remains **VECTOR** (autonomy is a level, not a version fork in the name); SSRN paper update out of scope for this cycle |

## 2. Council amendments (two audit sessions, 2026-07-14, validated)

**Session 1 — architecture audit (A1–A4):** the autonomy dial replacing a binary mode
(root cause: every gate verifies spec-conformance; the digest + navigate session preserve
*intent* verification at O(1) attention until L3 is earned) · supply-chain/injection
controls (pinned lockfiles, deps-guard escalation, builder without web tools, egress
restriction) · rollback as mechanism, not sentence (tag per merge + `vector-revert`
rehearsed in Phase A) · shadow mode as primary trust telemetry with the synthetic
benchmark timeboxed for defect-recall only.

**Session 2 — final audit (B1–B5):** Scope & Non-Goals stated as loudly as capabilities
(human retains legal/compliance; exit guarantee: standard repos, zero lock-in) · the
mock anti-drift rule (generated, disposable, never hand-edited; divergences fix the
spec — one contract, one oracle) · Act III as **bind-not-build** with three hard
requirements named before any ops design existed (production-injection controls,
live-data migration discipline, honest solo-ops) · method semver + per-project
`method_version` pin · the efficiency metric defined from project one (human-hours
head→production; cost per shipped feature).

**Post-freeze clarify (2026-07-15):** profiles replace the single-live-project premise ·
L3 as the author's starting default (sovereign choice; earned path recommended for
adopters) · subscription-mode budgets · the **ops cost ladder** (deterministic rules →
optional guardrailed local LLM → Claude human-invoked only — a resident frontier model
watching production is ruled out on cost and determinism grounds) · plugin distribution.

## 3. Pre-freeze executable validation (what was tested before believing)

| Track | Result |
|---|---|
| Hooks red-team | **47/47 across two rounds.** One real bypass found and fixed (flag-order attack on package installs → token parser, fail-closed). Four residual gaps documented, each mapped to a named downstream net (CODEOWNERS + conformance CI · coverage-ratchet · diff-based test-protection) — defense in depth verified, not asserted |
| Runner FSM | **8/8 scenarios** with the spec executed as a program: happy-path DAG, park-and-continue, immediate ambiguity escalation, review-deadlock, consecutive-failure breaker, **kill/resume identity from state alone**, L1 shadow semantics (level never self-raised), freeze-class spec-conflict |
| Consistency audit | 7 findings (invalid POLICY yaml block, undefined parse strategy, stale pre-dial flags, count drift, hook naming, two spec silences on breaker/budget accounting) — all resolved in the frozen artifacts |

The empirical layer (real agent build quality, escalation discipline, divergence rates,
detection recall, token economics) is deliberately **not** claimed: the phase gates below
are its test plan.

## 4. Rollout (implementation phases, each gated)

**Phase A — Deterministic gates, on the first pilot repo, at the project's starting
level.** Branch protection + required checks + CODEOWNERS; the three validated hooks;
test-protection CI; YAML reference; visual baselines; rollback tags + `vector-revert`
rehearsed; Reviewer in shadow if below L3. **Go/no-go:** in-repo red-team — an agent
provably cannot edit a frozen spec, delete a test, add a dependency silently, or merge
past a red check; one rehearsed revert.

**Phase B — Close the build loop (minimal Tier 2).** `/run-phase` dispatcher +
relay-runner (dispatch, spawn, poll, merge, tag, log, digest — nothing more) + rewritten
ship-issue/review-pr/solve-issue + `/escalate`. Pilot pure-session on 3–5 issues first,
then move to fresh processes. **Go/no-go:** clean resume after forced kill from state
files alone; tokens/issue measured; rate-limit pause/resume exercised.

**Phase C — Close the test loop.** Autonomous test-plan, `/explore` (Playwright),
fix-bugs auto, audit auto, phase auto-acceptance + digest/notification. **Go/no-go:**
the Explorer catches a deliberately injected UI↔endpoint mismatch.

**Phase D — L3 graduation evidence.** `/preflight-audit`, breaker tuning, and the
**timeboxed benchmark** (1 small app · 10 planted defects · 5 seeded ambiguities ·
~3 days). **Thresholds:** ≥95% issues merged without human touch · 0 spec violations
merged · detection recall ≥90% · 0 guessed ambiguities · (when graduating a project)
digest revert rate <2% over ≥50 merges.

**Phase E — Release.** `/promote` implemented for `vps-compose` (reference) — staging,
Explorer smoke, human GO, prod, verification, rollback. **Go/no-go:** one full promote +
one rehearsed production rollback on the pilot.

**Phase F — Operate.** The ops-pack + Tier D rules live on the pilot's production;
Step 19 calibration points executed on their dated triggers.

## 5. Residual risks (accepted knowingly)

- **False-green / intent gap** (dominant): gates verify spec-conformance; intent
  verification lives in the digest + navigate sessions and, at L3-from-day-one, in the
  human's deliberate acceptance of the residual. Rehearsed rollback and auditable phase
  reports are the backstop.
- **Test gaming:** hook + CI + ratchet + reviewer sign-off; perfect detection is not
  automatable.
- **Prompt injection / supply chain:** builder web tools disabled, dependencies pinned
  with deps-guard escalation, egress restriction recommended; production-side: the UGC
  sanitizer chain. Residual: injected content inside legitimate pinned documentation —
  accepted and monitored via digest.

## 6. Findings from the first pilot (`linksaver`, service-api, 2026-07-15)

The first end-to-end pilot (`vector-pilot-linksaver`, taken Act I → phase close with a subagent
playing the human at every gate) validated the machinery and surfaced two findings worth acting on:

- **The freeze checklist under-scrutinizes the error-response contract.** The phase-close Explorer
  (schemathesis) found 8 contract defects the frozen `api-spec.yaml` carried through Step 15 —
  undocumented `422`s, an `Error` schema that misdescribed the validation-error body, an over-loose
  `url`. The escalation-rate KPI doing its job, but pointed at the *design gate*: `/freeze-design`
  (Step 11) and `/preflight-audit` (Step 15) should assert **error-response completeness** — every
  operation documents its `4xx`/`422` responses and their schemas — not only that the YAML parses and
  the happy path maps. (Some of this is already implemented: `/freeze-design` now YAML-validates the
  frozen specs; the error-contract check is the open item.)
- **Any repo-visibility change silently drops branch protection (free plan).** Toggling the pilot
  repo private↔public removed DEV protection without warning, so a stretch of merges ran unenforced
  until it was re-applied. `/bootstrap-github` and Step-19 operations must **re-verify and re-apply
  branch protection after any visibility or plan change** — and the "CODEOWNERS backstops frozen
  paths" guarantee holds only while protection is actually applied (verified: with protection active,
  a frozen-path PR is correctly `BLOCKED` for a single identity; with it dropped, it merges CLEAN).
- **Code↔spec drift hides from the static-spec check; the promote smoke against the *live*
  `/openapi.json` caught it.** Exercising `/promote` end-to-end on a local deploy target (2026-07-15),
  the Step-18 smoke ran schemathesis against the running app's `/openapi.json` and found **6 real
  contract defects** the earlier "schemathesis green" (run against the hand-authored `api-spec.yaml`)
  had missed: Pydantic models lacking the spec's `pattern`/`maxLength`, a hand-rolled
  `422 {detail: "string"}` violating the documented `ValidationError` array shape, and undocumented
  404/409. Fixed code-in-line + one `/change-scope` (re-smoke 668/668). **Method refinement:** the
  phase-close Explorer — not only the promote smoke — must run against the live `/openapi.json` with
  `-c all`, and CI should assert `live-openapi ⊇ api-spec constraints` once code exists. Folding a
  *documented* status into a check's expected set (e.g. 409 for POST /tags) is contract-alignment, not
  gate-weakening (independently confirmed at the GO gate).
- **Act III is buildable and testable pre-production — bind-not-build confirmed.** The ops-pack
  (UGC-sanitizer, Tier-D rules evaluator, SQLite backup/restore, maintenance mode) was built and tested
  green (36 tests) on the pilot without a live prod, and a full `/promote` — staging → smoke → human
  GO → prod verify → **rollback recovered** — ran on a local deploy target with the ops-journal
  recording each event. Phase E/F machinery is now exercised; what remains before claiming them is a
  *real remote* target (network/TLS/reboot) and multi-project operating time.
