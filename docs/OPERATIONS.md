# Step 19 — Operate & Evolve (v2.0)

> Status: **design complete** (2026-07-15). Written before the first production deploy by
> explicit human decision (overrides the council's B3 deferral). Items that genuinely
> require production observation are **dated calibration points**, not design gaps.
> This is the full specification behind Act III of `docs/VECTOR.md`.

## Principles

**Bind, not build.** VECTOR generates configuration for boring commodity tools; it builds
no ops machinery of its own.

**The ops cost ladder** (the architectural spine of this step): a resident frontier model
watching production burns tokens without bound and adds no determinism. Operations are
therefore layered by cost:

- **Tier D — deterministic rules.** Always on, ~zero marginal cost. Fixed rules do all
  continuous monitoring.
- **Tier L — small local LLM (optional, off by default).** Guardrailed, read-only,
  summarization only.
- **Tier C — Claude, human-invoked only.** Never resident in production, never watching
  deploys. Appears exactly when the human calls it.

## The ops-pack (generated at Step 13 — operability is build-time)

Health endpoints · structured JSON logs with **user-generated-content fields tagged at
schema level** · error-tracker SDK wired (Sentry) · `ops/rules.yaml` (all thresholds) ·
uptime monitor config · backup cron (daily `pg_dump` → object storage, 30-day retention)
+ restore script · **sanitizer module** (strips/hashes UGC fields) · `MAINTENANCE.md`
runbook skeleton · `.vector/ops-journal.md` (one line per event, from first deploy).

## Tier D — deterministic rules (the default operator)

- Uptime probe on `/health`: 2 consecutive fails → page.
- Process supervision: compose `restart: unless-stopped` / systemd.
- Threshold alerts: disk >90% · sustained memory pressure · TLS cert <7 days ·
  backup-job failure · error-rate spike (error-tracker rule).
- Log pattern matchers for known-fatal signatures → page.
- All rules live in `ops/rules.yaml`; transport = Telegram bot;
  `notify.recipients` accepts one chat, a list, or a group id.

## Tier L — small local LLM (optional)

**Purpose:** nightly log/error clustering into one-paragraph digest summaries; severity
pre-classification of tracker issues. **Hard guardrails:** input only from the sanitized
stream; output is bounded JSON validated against a schema (discarded on violation); no
tools, no network, no actions; runs in its own resource-capped container; on failure the
system degrades to Tier D raw counts — Tier L can never block anything. Model: any small
local model (e.g. 3–8B via ollama); the choice is a calibration point.

## Tier C — Claude, human-invoked only

Entry points: the morning **`/triage`** (reads the digest + sanitized aggregates,
proposes actions, files `/report-bug` entries that flow into the severity matrix and the
existing P0 hotfix path) and **postmortem drafting** after incidents. Cost profile:
minutes per day, not agent-hours.

## Attention contract (solo-ops, honest)

- **Pages — immediate, no quiet-hour suppression** (the human manages silence on-device):
  total down · P0 signature · disk/cert/backup criticals.
- **Morning triage window (~30 min, weekday mornings):** the only scheduled ops
  attention — digest + accumulated alerts + tracker inbox + ops-journal.
  Weekends: pages only.
- **Digest:** deterministic, end of each run day and nightly once in production;
  repo file + Telegram push; recipients configurable.
- **Degradation defaults** when the human is unavailable: maintenance banner +
  read-only mode where the app supports it; feature-flag off as the scalpel.
  Documented per project in `MAINTENANCE.md`.

## Production-injection controls (hard requirement A)

User-generated content never enters agent context raw. Enforcement chain: UGC fields
tagged at log-schema level → sanitizer strips/hashes them → Tier L and Tier C consume
**only** the sanitized stream/aggregates → raw logs are human-eyes-only. Generated with
the ops-pack; verified in the preflight of the first `/promote`.

## Live-data migration discipline (hard requirement B)

Post-launch, any `/change-scope` touching the ERD triggers the migration playbook:
**expand-contract as separate deploys** (add-new → dual-write/backfill → switch-read →
drop-old) · backfill scripts with progress + resume · **rehearsal on an anonymized prod
snapshot in staging** (authorized) · a rollback point per stage · a migration checklist
gate added to that change's `/promote`. RPO 24 h (daily dump) accepted for project 1;
WAL/point-in-time recovery is a per-project POLICY upgrade.

## Incidents & evolution

Incidents enter via `/report-bug` (human- or alert-templated); the severity matrix
governs; P0 takes the hotfix path already defined in the fix policy; a postmortem line
goes to the ops-journal (Tier C drafts the long form if invoked). **Evolve:** intent
changes go through `/change-scope` — the frozen spec governs the application in
production, forever; new features are a new phase re-entering Act II at the project's
dial level; dependency updates arrive as deps-guard escalations resolved in a maintenance
phase. Exit guarantee intact: a standard repo on standard tools; VECTOR removable.

## Deploy profiles (cross-ref Step 18)

Chosen per project at Step 11. **`vps-compose`** (reference implementation, usual
default): compose + reverse proxy + systemd; staging = separate compose project with
synthetic seed. **`aws`** (defined at requirements level; reference implementation
deferred to the first AWS project): same pipeline semantics — staging, smoke, GO,
rollback — for projects whose compute or user scale demands it.

## POLICY ops keys (new section)

`deploy_target` · `notify.recipients[]` · `alert_rules: ops/rules.yaml` ·
`backup: {rpo: 24h, retention: 30d, restore_rehearsal: phase-close}` ·
`tier_l_enabled: false` · degradation default.

## Calibration points (dated — not gaps)

- **+2 weeks of production:** alert thresholds tuned against real traffic.
- **First month:** Tier L model + prompts tuned against real log shape (if enabled).
- **First post-launch ERD change:** migration playbook exercised end to end.
- **After the first incident:** attention-contract load review.

## Non-goals

No on-call rotation theater · no resident agents in production · no Kubernetes ·
no multi-region · no SLO dashboards nobody reads. "Robust" here means: an instrumented
app, deterministic nets, cheap rollback, and honest human attention.
