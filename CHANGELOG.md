# Changelog

All notable changes to the VECTOR method. Semantic versioning; every project pins `method_version` in its `POLICY.md` at design freeze.

## [2.0.0] — 2026-07-15

The autonomous release: v1 froze the design; v2 makes the frozen design executable without a human in the build loop, and extends the method to production. 15 steps → **19 steps across three acts** (Design / Build / Production).

### Added
- **The Act I driver, `/design`** — conducts sketches → PRD → wireframes → views → reference → ERD → OpenAPI → model specs → roadmap. Replaces v1's `SYSTEM_PROMPT.md`, which lived in a Claude Project's custom instructions and had no home once the surface consolidated.
- **Act II autonomy — three-tier architecture:** a Claude Code session as thin dispatcher (`/run-phase` + `/goal`), a deterministic Python relay-runner spawning one fresh `claude -p` process per role per issue, and repo-native gates that outrank every model's judgment.
- **The autonomy dial (L0–L3)** with data-earned graduation: L1 runs the reviewer in shadow mode (divergence vs. the human = trust telemetry); L2 adds autonomous merges + a mandatory daily digest with rehearsed revert authority + one `/how-to-navigate` per phase; L3 is full autonomy. Levels are raised only by the human.
- **`POLICY.md`** — the per-project autonomy contract, instantiated at design freeze: level, budgets, breakers, graduation thresholds, deploy profile, notification recipients, ops keys, `method_version` pin.
- **Deterministic gates:** three PreToolUse hooks (`frozen_specs`, `test_protection`, `deps_guard` — red-teamed with a 47-case battery; one real bypass found and fixed pre-release), CODEOWNERS on frozen paths, and CI checks (conformance via schemathesis + migrations↔ERD diff, security, coverage-ratchet, diff-based test-protection), enforced through branch protection under a dedicated machine user.
- **Step 9 — Interactive Mock:** a clickable prototype generated from the frozen-track artifacts (views + OpenAPI), used by the human before the freeze; generated, disposable, never hand-edited — divergences fix the spec. The intent check moved to where corrections cost minutes.
- **`/clarify` + the `[NEEDS CLARIFICATION]` marker convention** (Step 2): structured coverage-based interrogation; unresolved intent stays visible; zero live markers is a launch condition.
- **Step 15 — Preflight & Launch Authorization:** adversarial ambiguity scan, story↔endpoint↔view↔issue coverage matrix, environment dry-run, in-repo hooks red-team + rollback rehearsal.
- **Issues as executable contracts:** `verification:` blocks whose exit codes define done, model/complexity labels, dependency DAG, and a `.vector/issues.json` machine ledger.
- **The Explorer** (Playwright): network-level assertions that every UI action fires its exact mapped endpoint, edge batteries, and visual regression against approved baselines.
- **Escalation discipline:** six classes, park-and-continue scheduling, circuit breakers, kill-safe state (`state.json` authoritative; resume validated by simulation).
- **Rollback as mechanism:** an annotated tag per autonomous merge + scripted `vector-revert` opening a revert PR through the same gates.
- **Act III:** Step 18 — `/promote` release pipeline (staging → Explorer smoke → human GO → prod → verification → rehearsed rollback) with per-project deploy profiles (`vps-compose` reference, `aws`); Step 19 — Operate & Evolve, built on the **ops cost ladder** (deterministic rules → optional guardrailed local LLM → Claude human-invoked only), production-injection controls, live-data migration discipline, and an honest solo-ops attention contract.
- **Project profiles:** `webapp` complete; `service/api` defined as a strict subset; `cli/library` and `quant-pipeline` planned for 2.x.
- **Distribution as a Claude Code plugin** (`/plugin marketplace add fedeglan/vector` → `/plugin install vector`), with manual install fallback. The plugin installs the method; each repo instantiates the contract via `/vector:new-project`.
- **Subscription-mode operation:** budgets bind via turn/time limits; subscription rate-limit windows are handled as infra-pauses (park until reset, resume from state), never failures.

### Changed
- Canonical surface is **Claude Code end to end**; chat surfaces are a non-canonical ideation vestibule. `SYSTEM_PROMPT.md` folds into design-phase commands + `CLAUDE.md`.
- `api-frontend-reference` source of truth is now YAML (docx rendered from it).
- The method itself is versioned (this file); definition changes go through the method's own change-scope discipline.

### Validation
- Pre-freeze executable validation: hooks 47/47 across two red-team rounds (residual gaps mapped to named downstream nets); runner state machine 8/8 scenarios including kill/resume identity and shadow-mode semantics; POLICY parseability and cross-document consistency audited (7 findings resolved at freeze). Design council-audited twice (amendments A1–A4, B1–B5 integrated).

### Fixed — implementation hardening (2026-07-15, post-freeze; definition unchanged)
See `docs/audits/2026-07-15-repo-audit.md` for the full audit, evidence, and escalations.
- **`frozen_specs` hook fired only on relative paths** and so failed OPEN on the absolute
  `file_path` a live Claude Code session sends — an agent could edit any frozen spec, including
  raising its own `autonomy_level` in `POLICY.md`. Now normalizes paths against the project root.
- **Neither plugin agent registered** (`Agents (0)`): the manifest used an enumerated `agents`
  array, which Claude Code does not honor. Agents moved to a top-level `agents/` directory
  (auto-discovered); the discovery mechanism is now documented in the README.
- **`deps_guard`** let an unpinned install ride behind a leading pinned one
  (`pip install -r x && pip install evil`); now every chained segment is evaluated.
- **`test_protection`** missed bare test-directory deletes (`rm -rf tests`) and the `test_*.py`
  filename convention; both now blocked (false-positive-safe).
- All three hooks now handle malformed stdin cleanly instead of crashing to exit 1.
- Broken `<plugin>/…/hooks` paths in `setup.md`/`new-project.md` (missing `src/`) corrected;
  `service-api` profile token aligned in the command layer; `service-api` profile notes added
  to `freeze-design`/`explore`/`how-to-navigate`; unshipped-runner caveats added to
  `promote`/`preflight-audit`. New `redteam3.py` hardening battery wired into `make test`
  (the historical 47/47 across rounds 1–2 is preserved unchanged).

### Added — Act I completion + the merge-time gates (2026-07-15, post-freeze; definition unchanged)
The frozen method fully specified Steps 12–14 and the CI half of Tier 3, but no command
conducted them and the CI checks existed only as prose (audit finding H4). Now implemented:
- **`/generate-issues` (Step 12)** — derives `docs/GITHUB_ISSUES.md` + `.vector/issues.json`
  (self-contained issues with executable `verification:` blocks, labels, an acyclic DAG).
- **`/handover` (Step 13)** — the classic handover plus the merge-time enforcement layer as
  files (CI workflows, `CODEOWNERS`, the CI scripts) and the ops-pack.
- **`/bootstrap-github` rewritten for Step 14** — was v1-pure; now adds the `needs-human` /
  `escalated` labels, DEV branch protection with the six required checks, machine-user identity
  verification, and self-verifying asserts against the ledger.
- **The two logic nets as real code** — `src/orchestration/ci/coverage_ratchet.py` and
  `test_protection_ci.py` (diff-based), each with an executed red-team battery
  (`redteam_ci.py`, 18/18, in `make test`). They catch the edit-time hooks' documented
  residuals (whole-file test overwrites, early-return neutering, mv-rename-out). This makes
  "defense in depth is a verified property, not rhetoric" (SPEC §3.1) true rather than asserted.
- **CI + CODEOWNERS templates** — `src/templates/workflows/` (ci-tests, conformance, security,
  coverage-ratchet, test-protection) + `src/templates/CODEOWNERS`, webapp reference-stack,
  adapted per project by `/handover`.
Command count 26 → 28.

### Changed — definition coherence via /change-scope (2026-07-15)
First exercise of the method's own change-scope discipline on its frozen definition (see
`docs/change-scope/2026-07-15-definition-coherence.md`). No `method_version` bump (pre-release
coherence): profile token canonicalized to `service-api` in `VECTOR.md`; the dead
`STEP19_OPERATE_EVOLVE.md` pointer in `POLICY_TEMPLATE.md` repointed to `OPERATIONS.md`; the
`@`-reference read-deny guidance removed from `SPEC.md`/`VECTOR.md` (the threat model is writes,
which are hooked regardless of how a file entered context; the deny blocked legitimate reviewer
reads and closed nothing).

### Not yet shipped
- **The Tier-2 relay-runner** is the Phase B deliverable. 2.0.0 ships its build contract and its executable specification (`src/orchestration/runner/tests/fsm_sim.py`). Until it lands, Act I and the Tier-3 gates are fully usable and Act II runs at L0/L1 — human-driven `/ship-issue`, with the gates enforcing the contract underneath.
- Profiles `cli/library` and `quant-pipeline` (2.x). Step 19's reference implementation binds at the first real deploy (Phase F); the spec is complete.

## [1.x]

The published 15-step method: visual-first design, machine-verifiable artifacts, design freeze, GitHub-native issue generation, and the human-in-the-loop build/test loop (`/ship-issue`, `/test-plan`, `/how-to-navigate`, `/fix-bugs`).
