# Change-scope: definition coherence (2026-07-15)

> The first exercise of VECTOR's `/change-scope` discipline **on VECTOR's own frozen
> definition**. Three corrections to the frozen 2.0.0 method, bundled with impact analysis,
> approved by the author (Federico), applied together. Origin: escalations M1, L1, L7 of
> `docs/audits/2026-07-15-repo-audit.md`.

## 0. Is this even a change-scope? (the honest test)

`/change-scope` exists so that *design* changes are deliberate; it must not be used to paper
over an implementation bug (see `change-scope.md` hard rules). All three items here are
genuine defects **in the frozen artifacts themselves** — a self-contradiction between two
frozen files, a dead file pointer, and a guidance line that instructs a control that blocks
legitimate work and closes nothing. None is an implementation bug being masked. So the
sanctioned path is correct. The definition is unreleased (2.0.0 lives on `v2`, not `main`),
so these are pre-release coherence corrections, **not** semantic evolution.

## 1. The changes, precisely

| # | Frozen artifact | From | To |
|---|---|---|---|
| 2 | `docs/VECTOR.md` (L9, L129) | profile token `service/api` | `service-api` |
| 3 | `src/templates/POLICY_TEMPLATE.md` (L218) | `docs/STEP19_OPERATE_EVOLVE.md` | `docs/OPERATIONS.md` |
| 4 | `src/orchestration/SPEC.md` (§3.1) & `docs/VECTOR.md` (Step 13, L62) | "settings deny-rules cover the `@`-reference read gap" | *removed* |

**Why each:**
- **(2) Canonical profile token.** Frozen `VECTOR.md` said `service/api`; frozen
  `POLICY_TEMPLATE.md` said `service-api`. Two frozen files cannot both be canonical. The
  token lives in POLICY YAML and in a `--profile` CLI flag, where a slash is fragile
  (path/label/flag parsing); the runner parses the POLICY value. Canonical = **`service-api`**.
- **(3) Dead pointer.** `docs/STEP19_OPERATE_EVOLVE.md` never existed; the Step-19 spec is
  `docs/OPERATIONS.md` (its H1 is "Step 19 — Operate & Evolve"). Pre-rename filename.
- **(4) Deny-rule guidance removed.** The `@`-reference is a *read* mechanism; the threat
  model is *writes*, and Edit/Write/MultiEdit/Bash are hooked regardless of how a file
  entered context. A `permissions.deny` on frozen-path **reads** blocks the reviewer's and
  builder's legitimate reads (they must read the specs to check conformance) while `cat`/`grep`
  still read them — so it obstructs real work and closes nothing.

## 2. Impact analysis (blast radius)

- **(2)** Non-frozen files already aligned to `service-api` in the hardening pass
  (`new-project.md`, `design.md`, `mock.md`, `upgrade-project.md`, `POLICY_TEMPLATE.md`).
  Remaining to align for consistency (this bundle): `docs/VECTOR.md` (frozen),
  `docs/DECISIONS.md`, `README.md`. No command *parses* the prose token, so no runtime break;
  the risk was a future command branching on the wrong literal. After this bundle, one token
  everywhere. **No issues affected** (no project has frozen against this yet — 2.0.0 unreleased).
- **(3)** `POLICY_TEMPLATE.md` is copied verbatim into every instantiated project; the dead
  pointer would propagate. One project has frozen against it: **none**. Pure documentation
  pointer; no endpoint/ERD/reference coupling.
- **(4)** Removing the deny-rule guidance touches frozen `SPEC.md` §3.1 and `VECTOR.md` Step 13,
  plus implementation (`hooks.json` `_deny_rules_note`, `new-project.md` §3,
  `upgrade-project.md` §3). No frozen *spec* (endpoint/ERD/view) depends on it. The edit-time
  hooks (`frozen_specs` et al.) remain the mutation control; `CODEOWNERS` remains the
  merge-time control. Net security posture is **unchanged** for writes and **improved** for
  legitimate reads. The four documented hook residuals are unaffected (they are write-path).

Cross-consistency after the change: endpoints ↔ reference ↔ views ↔ ERD untouched (none of
the three items is a spec of the application domain). Roadmap phase boundaries: unaffected.

## 3. Approval

Author (Federico) approved all three explicitly on 2026-07-15, with the reasoning above
(service-api canonical; STEP19→OPERATIONS confirmed; deny-rules removed because @-reference
only reads and writes are already hooked).

## 4. Version decision

**No `method_version` bump; no re-tag.** These are pre-release coherence corrections to an
unreleased 2.0.0 (still on `v2`, not merged to `main`). `change-scope.md` step 4 re-tags "if
the change is material" — none of these alters method semantics, artifacts consumed/produced,
or the gate set. The corrected 2.0.0 is the one that will be released. CHANGELOG records the
correction under the 2.0.0 entry.

## 5. Verdict on the discipline itself (Federico asked)

`/change-scope` held up as a process for a method-level correction: stating the change,
tracing the blast radius, and requiring approval caught that item (4) touches *two* frozen
files plus three implementation files — a coupling that a "just fix the typo" reflex would
have missed, leaving `VECTOR.md` Step 13 still advertising a control we removed. The one gap:
the command is written for *project* specs (endpoint↔reference↔ERD tracing, issue re-queue by
timestamp) and has no explicit branch for a *method-level* change-scope (amend the definition
itself, no issues to re-queue). That is a documentation gap in `change-scope.md`, noted here,
not a blocker — the discipline transferred cleanly.
