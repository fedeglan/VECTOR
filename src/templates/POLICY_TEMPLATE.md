# POLICY.md — Template (VECTOR v2.0.0)

> Instantiated per project at **Step 11 (Design Freeze)**. This file is the project's
> autonomy contract: the runner parses it at startup and **fails fast** on missing keys.
>
> **Parse strategy (machine vs. human layer):** the runner parses **only the fenced
> `yaml` blocks**, keyed by the nearest preceding `##` heading. Markdown tables are
> human-facing mirrors; decision matrices (fix severity, model pairing) are implemented
> runner-side in code — the tables here document them, they do not configure them.

```yaml
method_version: 2.0.0        # pinned at freeze — a design frozen against a floating method is not frozen
project: "{{PROJECT_NAME}}"
profile: webapp              # webapp | service-api
frozen_at: "{{ISO_DATE}}"
```

## 1. Autonomy level (the dial)

```yaml
autonomy_level: L1           # L0 | L1 | L2 | L3 — raised ONLY by the human, never by the loop
```

- **L0 — classic HITL.** v1 behavior: human reviews and merges every PR.
- **L1 — HITL + gates.** Human still reviews every PR, but Tier-3 gates are live and the
  Reviewer agent runs in **shadow mode**: its verdict is recorded per PR and compared with
  the human's — the divergence rate is the trust telemetry that earns L2.
- **L2 — supervised autonomy.** Merges to DEV are autonomous through the full gate
  sequence. Intent verification survives at O(1) attention: a **mandatory daily digest**
  with rehearsed revert authority, plus **one required `/how-to-navigate` per phase**.
- **L3 — full autonomy.** Digest optional (recommended ON for a project's first run);
  escalations and phase reports only.

The starting level is the human's sovereign choice; the earned path below is the
recommended default for new adopters.

```yaml
graduation:                  # defaults — tune with real telemetry
  l1_to_l2: gates red-team passed AND shadow divergence < 10% over >= 20 PRs
  l2_to_l3: digest revert rate < 2% over >= 50 merges AND timeboxed benchmark passed
  rule: graduation is a human action, logged here with date; the loop never raises its own level
```

## 2. Orchestration

```yaml
tiers: session-dispatcher / relay-runner / deterministic-gates
run_window: "08:00-24:00"    # local; runner refuses to start outside it
session_rotation_context: 0.5  # Tier-1 context fraction that triggers checkpoint + rotation
```

## 3. Permission & supply chain

```yaml
permissions: explicit allow-rules; no blanket bypass where avoidable
disallowed_tools_builder: [WebFetch, WebSearch]   # unattended builders consume no arbitrary web content
sandbox: optional            # dev-container, non-root, project-only mount — recommended if bypass is ever used
secrets: .env only, never in repo, never in agent context
```

```yaml
supply_chain:
  dependencies: pinned at Step 12 — lockfiles are frozen artifacts
  new_dependency: escalation via deps-guard hook, never silent adoption
  tier2_egress: restrict to package registries + GitHub + Anthropic API (OS/container level, never model level)
```

## 4. Budgets

```yaml
budgets:
  build_attempts: 3          # CI-red retries consume this same budget
  review_cycles: 2           # third rejection = escalation
  minutes_per_issue: 60
  hours_per_run: 8
billing:
  mode: subscription         # subscription | api
  subscription: rate-limit windows are infra-pauses — park until reset, resume from state; never a failure or breaker event
  api_caps: {per_run_usd: null, per_month_usd: null}   # set only when mode: api
telemetry: tokens and wall-time logged per issue (efficiency ledger)
```

## 5. Circuit breakers

```yaml
breakers:
  consecutive_terminal_failures: 3   # halts the run. Issue-level: one terminal failure counts once.
                                     # Only budget-class failures feed this counter; ambiguity,
                                     # review-deadlock and spec-conflict escalations do NOT —
                                     # they are design signals, not build instability.
  same_test_fix_attempts: 3          # then escalate the test itself
  freeze_class: [critical-security-finding, spec-conflict blocking > 50% of remaining DAG]
```

## 6. Merge policy

```yaml
merge:
  target: DEV                # terminal for autonomy; main/deploy are human-only via /promote
  required_checks: [ci-tests, conformance, security, coverage-ratchet, test-protection, reviewer-approval]
  bot_identity: "{{MACHINE_USER}}"   # dedicated GitHub machine user; least privilege
  tag_per_merge: vector/T<NNN>I<N>   # annotated tag on every autonomous merge
```

Note: `tests/**` is deliberately NOT under CODEOWNERS — every issue writes tests, and
human approval there would reintroduce per-PR review. Test protection is enforced by the
PreToolUse hook (edit time) and the `test-protection` check (merge time).

Rollback (autonomous merges are only safe if reverts are cheap and rehearsed):

```yaml
rollback:
  revert: scripted — vector-revert <tag> opens a revert PR through the SAME gate sequence (never a force-push)
  rehearsal: executed in the Phase A red-team; re-verified at every phase close
  authority: at L2, the digest reviewer may trigger a revert unilaterally
```

## 7. Review policy

```yaml
review:
  pairing: {haiku: sonnet, sonnet: opus, complexity_high: opus}   # reviewer tier >= builder tier
  checklist: full            # always — no abbreviated reviews in autonomous mode
  test_delta_inspection: mandatory
  context: diff + issue + specs only — never the builder's transcript
  summary: plain-language, captured at review time (feeds the digest)
```

## 8. Testing policy (phase close)

```yaml
testing:
  suites: [fast, thorough]
  failure_classification: [code-bug, test-bug, flaky, spec-conflict]
  flaky_retries: 2           # then quarantine + auto-filed issue
  test_bug_fix: requires signed justification + reviewer sign-off on the delta
  spec_conflict: escalate — never resolved by choice
```

## 9. Explorer policy

```yaml
explorer:
  engine: playwright         # network interception + screenshots; Claude in Chrome is human-interactive only
  smoke_cadence: every 10 merges (rounds 1+3)
  full: 4 rounds at phase close
  visual_threshold: {mvp: functional-only, v1_plus: ">=2% area = P3"}
  a11y: AA informational (non-blocking) in MVP
  evidence: screenshot + network log attached to every finding
```

`/how-to-navigate` is **required once per phase at L2** (the human intent check) and
opt-in at L3.

## 10. Fix policy

| Severity | Meaning | Handling (runner-side matrix) |
|---|---|---|
| P0 | Flow broken | Hotfix path, one per batch, immediately |
| P1 | Wrong/failed endpoint | Fix batch, this phase |
| P2 | State/UX anomaly | Fix batch, this phase |
| P3 | Visual over threshold | Defer allowed, logged with justification |

Every fix PR passes the full Step-16 gate sequence; deferrals are logged.

## 11. Phase gate

```yaml
phase_gate:
  mode: notify-and-continue
  acceptance: {p0: 0, p1: 0 or justified deferral, audit: clean}
```

## 12. Escalation, control plane & state

```yaml
escalation:
  classes: [spec-conflict, ambiguity, budget, infra, security, review-deadlock]
  scheduling: park-and-continue    # dependents blocked; independent DAG branches continue
  return_path: spec-conflicts re-queue only after /change-scope (timestamp-enforced)
control:
  halt: Esc or .vector/HALT (takes effect at next issue boundary)
  resume: /run-phase — .vector/state.json is authoritative and kill-safe
notification:
  hook: telegram             # optional, one-way
  events: [escalation, breaker, phase-report, run-summary, page]
  recipients: []             # one chat id, a list, or a group id
digest:
  required_at: [L2]          # recommended ON at L3 for a project's first run
  cadence: daily
  target_attention_minutes: 20
email: disabled
```

## 13. Release (Step 18)

```yaml
release:
  deploy_target: vps-compose   # vps-compose | aws — chosen per project at freeze
  staging: separate environment, synthetic seed
  smoke_gate: explorer against staging
  go: human, terminal-only     # the single production human gate
  post_verify: health + smoke
  rollback: rehearsed (deploy rollback + vector-revert discipline)
```

## 14. Operations (Step 19)

```yaml
operations:
  ladder: [tier-d-deterministic, tier-l-local-llm-optional, tier-c-claude-human-invoked]
  alert_rules: ops/rules.yaml
  pages: [total-down, p0-signature, disk-cert-backup-criticals]   # immediate; human manages silence on-device
  triage_window: weekday mornings ~30 min
  backup: {rpo: 24h, retention: 30d, restore_rehearsal: phase-close}
  tier_l_enabled: false
  degradation_default: maintenance-banner + read-only
  ugc: never enters agent context raw — sanitizer chain per docs/STEP19_OPERATE_EVOLVE.md
```

## 15. Invariants (no tier may override these)

1. Specs are law; the only mutation path is `/change-scope`.
2. Builder ≠ reviewer — fresh process per role; reviewer tier ≥ builder.
3. Deterministic gates outrank model judgment.
4. Every fix ships a regression test.
5. Tests are protected artifacts.
6. Everything is budget-bounded.
7. Full traceability — JSON-authoritative state; `SESSIONS.md`/`ESCALATIONS.md` as human mirrors.
