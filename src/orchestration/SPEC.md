# ORCHESTRATION SPEC — VECTOR v2.0.0 (Act II, the three tiers)

> Frozen 2026-07-15. Supersedes any prior runner spec.
> Behavior is level-dependent (POLICY §1): **L1** — pipeline runs with the Reviewer in
> shadow mode and the human merging. **L2** — autonomous merges + daily digest + one
> required `/how-to-navigate` per phase. **L3** — as fully specced below. The runner
> reads the level at startup and **never raises it**.

## 0. Architecture — why three tiers

| Tier | What | Why |
|---|---|---|
| 1 | A Claude Code **session** as thin dispatcher (`/run-phase` + `/goal`) | The v1 UX: open, run, watch, intervene. `/goal` is a continuation mechanism, never a verifier |
| 2 | A deterministic Python **relay-runner** spawning one fresh `claude -p` per role per issue | Fresh context per unit of work; hard turn/time caps exist in print mode; kill-safe state on disk |
| 3 | **Deterministic gates** — hooks, branch protection, CODEOWNERS, CI | They outrank every model's judgment; merge is mechanically impossible past a red check |

Rationale (research-verified): `/goal` and `/loop` are official but session-scoped and
non-verifying; long single sessions degrade under compaction; hard caps (`--max-turns`)
exist only in print mode; Anthropic's own long-running harness uses fresh contexts with
JSON state on disk. Hence: session for UX, relay for execution, external gates for safety.

## 1. Tier 1 — the dispatcher

`/run-phase` reads `POLICY.md` + `.vector/state.json` + `.vector/issues.json`, sets
`/goal` to the phase acceptance condition, launches/monitors the relay, and narrates
progress. The human can type at any moment. At >50% context or on compaction: checkpoint
+ session rotation (POLICY §2). Also runnable standalone: `vector-run start|resume|status|halt`.

## 2. Tier 2 — the relay-runner

Deterministic Python. Scope is deliberately minimal — dispatch, spawn, poll, merge, tag,
log, digest, revert — and stays that way: anything more competes with what the platform
may ship natively. Persists `.vector/state.json` after **every** transition —
kill/reboot-safe by requirement (validated by simulation: resume from state alone
reproduces the uninterrupted run).

### 2.1 Startup
Parse POLICY per its declared strategy — fenced yaml blocks keyed by nearest `##`
heading; **fail fast** on missing keys; decision matrices (fix severity, model pairing)
are code, the POLICY tables are mirrors. Load the issue ledger. Verify `gh` is
authenticated as the machine user. Refuse to start outside `run_window`.

### 2.2 Scheduling & budgets
Ready set = `queued` issues whose dependencies are all `merged`. Per-issue caps via
`--max-turns` and wall-time; per-run cap via `hours_per_run`. **Billing modes:** under
`subscription`, rate-limit windows are detected and handled as **infra-pauses** — the
runner parks until the window resets and resumes from state; never a failure, never a
breaker event. Under `api`, optional USD caps apply. Tokens + wall-time are logged per
issue regardless (the efficiency ledger).

### 2.3 Per-issue pipeline
1. Pick next ready issue.
2. **Build.** `claude -p "/ship-issue T<NNN>I<N>"` — fresh process, model per issue
   label, level context injected by the runner. Branch from DEV → implement per the
   self-contained prompt → tests + `verification:` self-check → push → PR → structured
   JSON exit. Exit `blocked` (ambiguity) → escalate **immediately**, single attempt, no
   retries.
3. **CI wait.** Red → classify: test/build failure → next attempt with the failure log
   attached; CI infra failure → retry once, then escalate `infra`. **CI-red retries
   consume the same `build_attempts` budget** — there is no hidden retry pocket.
4. **Review.** `claude -p "/review-pr <PR>"` — fresh context: diff + issue + specs only,
   never the builder's transcript. Full checklist, mandatory test-delta inspection,
   verdict + plain-language summary (feeds the digest). Runner sets the
   `reviewer-approval` **status check** via the bot identity. **At L1 (shadow mode):**
   the verdict is recorded to `.vector/shadow.json` and later compared with the human's
   decision on the same PR — the divergence rate is the graduation telemetry; the check
   is informational and the human remains the merger.
5. **Fix cycle.** Changes requested and cycles remain → builder fix process on the same
   branch with the numbered blockers as input → back to 3. Third rejection → escalate
   `review-deadlock` with both positions attached.
6. **Merge.** All required checks green → `gh pr merge --merge --delete-branch`, close
   issue with PR link, checkout DEV. Every autonomous merge gets an annotated tag
   `vector/T<NNN>I<N>` — the rollback handle (§2.6). Deterministic `SESSIONS.md` entry.
7. **Cadence.** Every 10 merges → `/audit-plan` (blockers auto-file fix issues) +
   Explorer smoke (rounds 1+3).

### 2.4 Escalation & breakers
Classes: `spec-conflict | ambiguity | budget | infra | security | review-deadlock` →
entry in `ESCALATIONS.md` with the exact decision needed phrased as a question,
`needs-human` label, optional notify. **Park-and-continue:** dependents blocked,
independent DAG branches continue. **Breaker counting (issue-level):** an issue's
terminal failure counts **once** toward `consecutive_terminal_failures`; only
budget-class failures feed the counter — ambiguity, review-deadlock and spec-conflict
escalations do **not** (design signals, not build instability). A merge resets the
counter. **Freeze-class** (halt the phase): critical security finding; spec-conflict
blocking >50% of the remaining DAG. **Return path:** spec-conflicts re-queue only after
`/change-scope` (freeze-marker timestamp enforced). **Halt:** Esc or `.vector/HALT`,
effective at the next issue boundary. **Resume:** state on disk is authoritative.

### 2.5 Phase close
When every phase issue is `merged` or `escalated`/blocked, the runner orchestrates the
Step-17 sequence (audit → fast tests with failure classification → `/explore` full →
`/fix-bugs` matrix → thorough → acceptance → phase report → notify-and-continue). Each
fix PR re-enters the §2.3 pipeline.

### 2.6 Rollback mechanics
Autonomous merges are only safe if reverts are cheap and rehearsed. `vector-revert <tag>`
opens a revert PR that passes through the **same** gate sequence (§2.3 steps 3–6) —
never a force-push. Executed once in the Phase A red-team; re-verified at every phase
close. At L2, the digest reviewer's revert authority maps to this script.

### 2.7 Digest
Generated deterministically (no LLM call): merges since last digest (issue id, the
reviewer's plain-language summary captured at review time, files, cost), escalations
opened/resolved, revert handles. Written to `.vector/digest/<date>.md`, pushed via the
notify hook if enabled. Mandatory at L2; recommended ON at L3 for a project's first run.
Reading it is the human's O(1) intent check; no action is required for the loop to
continue.

## 3. Tier 3 — deterministic gates

### 3.1 Hooks (PreToolUse; edit-time layer)
Hooks are language-agnostic executables; the **reference implementation is python3**
(macOS ships no jq; JSON-in-bash without jq is fragile). The validated `.py` files and
their red-team batteries ship in `src/orchestration/hooks/`.

| Hook | Fires on | Blocks (exit 2) |
|---|---|---|
| `frozen_specs` | Edit/Write/MultiEdit/Bash | Any mutation of frozen design artifacts (specs, POLICY, baselines) — shell redirection, sed -i, cp/mv/rm included |
| `test_protection` | Edit/Write/MultiEdit/Bash | Test deletion, skip/xfail insertion, assertion-count reduction, test-case removal |
| `deps_guard` | Edit/Write/Bash | Manifest/lockfile mutation; package-adding installs (token parser, fail-closed; pinned installs pass) |
| `budget-counter` | PostToolUse | Maintains on-disk attempt/cycle counters |
| `notify` | Notification/Stop | Optional one-way Telegram ping (POLICY §12) |

Frozen artifacts are read freely (the reviewer and builder must read the specs to check
conformance); the threat model is **writes**, and Edit/Write/MultiEdit/Bash are hooked
regardless of how a file entered context, so no read-side `permissions.deny` is needed.
Known residual gaps in the edit-time hooks (inline-language writes, constructed paths,
early-return test neutering, whole-file test overwrites) are each covered by a named
downstream net: CODEOWNERS + conformance CI, the coverage-ratchet, and the diff-based
`test-protection` CI check — defense in depth is a verified property, not rhetoric
(the two logic nets ship in `src/orchestration/ci/` with their own executed red-team battery).

## 3.2 CI required checks (merge-time layer)
`ci-tests` (the pyramid) · `conformance` (schemathesis endpoints↔OpenAPI; migrations↔ERD
diff; import-linter architecture rules) · `security` (gitleaks + bandit/pip-audit or npm
audit) · `coverage-ratchet` (coverage may never drop — the net for neutered tests) ·
`test-protection` (diff-based deletions/skips/weakening detector requiring a signed
justification block) · `reviewer-approval` (status check set by the runner).

### 3.3 Permission configuration
Explicit `permissions.allow` rules, no blanket bypass where avoidable. **Never rely on
`--allowedTools` under `bypassPermissions`** (ignored — open platform issues);
`--disallowedTools` and hook denies do hold. **Builder invocations run with web tools
disallowed** (`WebFetch`, `WebSearch`); documentation comes from pinned dependency
versions. Tier-2 egress restricted at OS/container level to registries + GitHub +
Anthropic API where feasible. Optional dev-container sandbox if bypass is ever required.

### 3.4 Branch protection & identities
DEV protected with the required checks (POLICY §6); merges via a dedicated **machine
user** with least privilege; CODEOWNERS on frozen paths + `POLICY.md` only — deliberately
**not** on `tests/**`. Exact platform flags re-verified against official docs at
implementation time (the platform ships weekly).

## 4. The Explorer
Playwright (CLI or MCP): four rounds at phase close, smoke (rounds 1+3) every 10 merges.
Round 1 walks every row of `api-frontend-reference.yaml` per role with **network
interception asserting the exact mapped endpoint + method**; rounds 2–4: edge battery,
PR-flagged views, visual diff vs `baselines/` at 3 viewports + a11y. Findings →
`BUG_BACKLOG.md` in `/report-bug` format with **screenshot + network log attached**.
Claude in Chrome is not used here (interactive prompts, real profile, no clean
interception); it remains the human's tool via `/how-to-navigate` — mandatory once per
phase at L2, opt-in at L3.

## 5. State & files
`.vector/`: `state.json` (authoritative), `issues.json` (ledger), `shadow.json` (L1
telemetry), `digest/`, `HALT` (control), `ops-journal.md` (post-launch). Human mirrors:
`SESSIONS.md`, `ESCALATIONS.md`. JSON is deliberately the machine format — models tamper
with it less than with Markdown, and it diffs cleanly.
