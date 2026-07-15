# /change-scope

The *only* sanctioned way to change a frozen spec after the Design Freeze. Everything downstream trusts the freeze; this command is the controlled mutation that keeps that trust intact. In v2 it also gates the re-queue of any issue that was parked on a spec-conflict.

## When
- The human wants a design change after the freeze.
- A spec-conflict escalation requires a frozen spec to actually change to be resolved.

## What you do

### 1. State the change precisely
Write what changes, in which frozen artifact, and why. If this originated from an escalation, link it.

### 2. Impact analysis
Trace the blast radius before touching anything:
- Which other frozen specs are affected (endpoint ↔ reference ↔ views; migration ↔ ERD)?
- Which issues — done, in-flight, or queued — are invalidated or need to change?
- Does the roadmap phase boundary move?
Present this to the human. A scope change with an unexamined blast radius is how a frozen contract quietly rots.

### 3. Human approval
The human approves the change and its impact. Do not proceed on your own judgment — this is a frozen-spec edit, the one thing the whole method is built to make deliberate.

### 4. Apply — through the freeze, not around it
- **Open the sanctioned mutation window**, edit, then close it — the `frozen_specs` hook blocks
  frozen-spec edits at all other times, so this is the one exception and it must be explicit:
  ```bash
  mkdir -p .vector && touch .vector/change-scope-open   # the hook now permits frozen-spec edits
  # ... update the frozen artifact(s) ...
  rm -f .vector/change-scope-open                        # close it immediately — never leave it open
  ```
  The window is narrow by design and CODEOWNERS still requires the human's review on the frozen
  paths at merge time (defense in depth). Never leave `.vector/change-scope-open` committed or
  lingering — it is a transient control, not a config file (it is gitignored by `/new-project`).
- Update the freeze marker / `method_version` context and re-tag if the change is material.
- Regenerate or amend the affected issues in `GITHUB_ISSUES.md` and `issues.json`.
- If the mock still exists and the change is UI-facing, regenerate it (never hand-edit).

### 5. Re-queue
Any issue parked on the resolved spec-conflict may now re-queue. The runner enforces this by timestamp: an issue re-enters only after the freeze marker's update time is newer than the escalation. This prevents building against a spec that hasn't actually changed yet.

## Hard rules
- No frozen-spec change without impact analysis and human approval.
- Do not use `/change-scope` to paper over an implementation problem that isn't actually a spec problem. If the spec is right and the code is wrong, that's a bug, not a scope change.
- Keep the specs internally consistent after the change — a partial edit that leaves endpoints and reference disagreeing is worse than no edit.
