# /run-phase

The Act II dispatcher. You are Tier 1: a thin controller that launches and monitors the deterministic relay-runner while it builds an entire phase autonomously. You do not implement issues yourself — you dispatch, narrate, and surface escalations.

## Usage
```
/run-phase [<phase-name>]
```
Defaults to the next incomplete phase in `docs/roadmap.md`.

## Before you start
Read `POLICY.md` in full — it is the contract. Confirm:
- `autonomy_level` (L0/L1/L2/L3) — this governs everything below.
- Budgets, breakers, the deploy profile, notification recipients.
- `.vector/state.json` exists (resume) or the phase is clean (fresh start).
- `.vector/issues.json` is present and consistent with the GitHub board.

If `POLICY.md` is missing a required key or does not parse, STOP and tell the human — do not improvise defaults.

## What you do

### 1. Set the goal
Set `/goal` to the phase's acceptance condition from POLICY §11 (0 P0 · 0 P1 or justified deferral · audit clean). `/goal` is a continuation mechanism — it keeps the loop going — **not** a verifier. Verification is the gates, never the goal check.

### 2. Launch the runner
> **Until Phase B lands, the relay-runner does not exist.** If `vector-run` is not on PATH, do not improvise a substitute and do not pretend the loop is running. Say so, and offer the honest fallback: drive the phase at L0/L1 the v1 way — `/ship-issue` per issue in dependency order, with the human merging each PR. The gates (hooks, CI, branch protection) are fully live and enforce the contract underneath, so the work is still VECTOR-grade; what is missing is the autonomy, not the discipline.

Start the relay-runner for this phase:
```bash
vector-run start --phase <phase-name> --level <autonomy_level>
```
The runner spawns fresh `claude -p` processes per role per issue (builder, then reviewer at the paired tier), waits on CI, merges through the gates, tags each merge, and persists state after every transition. You monitor its output.

### 3. Monitor and narrate
As the runner reports progress, keep the human oriented: which issue is building, which merged, current cost, how many remain. Do not intervene in a healthy loop.

### 4. Handle what reaches you
- **Escalation** (`ESCALATIONS.md` gets an entry): surface it to the human immediately with the exact decision needed. The runner has already parked that issue and continued with independent work. Do not answer on the human's behalf. A spec-conflict must go through `/change-scope` before its issue re-queues.
- **Breaker trip** (3 consecutive terminal failures, or freeze-class): the run has halted. Report why, show the state, and wait for the human.
- **Context pressure** (>50%): checkpoint and rotate the session per POLICY §2.

### 5. Level-specific duties
- **L1:** the reviewer runs in shadow; the human merges each PR. Present each PR with the reviewer's verdict and record the human's decision (the divergence is graduation telemetry).
- **L2:** merges are autonomous. Generate the daily digest (deterministic) and ensure the human runs `/how-to-navigate` once this phase.
- **L3:** escalations and the phase report only.

### 6. Phase close
When every issue is `merged` or parked, the runner triggers `/audit-plan` → fast tests → `/explore` → `/fix-bugs` → thorough tests → acceptance (Step 17). Report the phase result and, per POLICY, notify-and-continue to the next phase or stop for the human.

## Controls (tell the human these exist)
> Until the Phase-B runner ships, the `vector-run` controls below do not exist. Pre-Phase-B, the
> live control is **Esc** (and `.vector/HALT` only matters once a runner is polling for it).
- Halt: Esc, or (once the runner is installed) `vector-run halt` (writes `.vector/HALT`; stops at the next issue boundary).
- Resume: `/run-phase` or (once installed) `vector-run resume` — `.vector/state.json` is authoritative and kill-safe.

## Hard rules
- You never raise the autonomy level. Only the human does, in POLICY, on graduation evidence.
- You never merge to main or deploy — that is `/promote`, human-gated.
- You never edit a frozen spec or resolve a spec-conflict by choice — you escalate.
