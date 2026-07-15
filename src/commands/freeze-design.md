# /freeze-design

Execute the Design Freeze (Step 11) — the moment the specs stop being drafts and become a contract. This is a human-approval gate; you prepare everything, the human authorizes the freeze.

## Preconditions — verify all
- The mock gate passed (Step 9): the human confirmed the fake app matches intent.
- Every frozen-track artifact exists: `PRD.md`, `views.md`, `api-frontend-reference.yaml`, `erd.dbml`, `api-spec.yaml`, and any `research/msd_*.md`.
- The roadmap (Step 10) assigns every user story to a phase.

## What you do

### 1. Generate CONTEXT.md
Synthesize the project bible: module map, naming conventions, architecture patterns (mandatory and forbidden), the layering rules, and the stack. This is what every builder and reviewer reads.

### 2. Instantiate POLICY.md
Copy the template and fill it *with the human* — this is the autonomy contract and its values are the human's to set:
- `autonomy_level` — the starting level (the human's sovereign choice; L1→L2→L3 is the recommended earned path).
- Budgets, breakers, graduation thresholds.
- Explorer cadence and visual thresholds.
- `deploy_target` (`vps-compose` | `aws`), notification recipients.
- Pin `method_version` (the installed VECTOR plugin version) and `frozen_at`.
Then parse it once to confirm it is valid (fail-fast): the runner will refuse to start otherwise.

### 3. Archive the baselines
Copy the approved Step-4 renders to `baselines/`. These become the Explorer's visual oracle — they must be the exact renders the human approved.

### 4. Walk the freeze checklist
Confirm: specs cross-consistent (endpoints ↔ reference ↔ views; migrations ↔ ERD), no orphan endpoints, no unresolved `[NEEDS CLARIFICATION]` markers in frozen-track files. **Assert the frozen YAML actually parses** — "YAML is the source of truth" only if it loads: `python3 -c "import yaml,sys; [yaml.safe_load(open(f)) for f in ['docs/api-spec.yaml','docs/api-frontend-reference.yaml']]"` must exit 0. (An unquoted `{id}` in an inline flow-mapping, e.g. `path: /links/{id}/tags`, silently makes the file invalid YAML; quote such values.)

### 5. Tag
```bash
git add -A
git commit -m "freeze: design contract — method_version <x.y.z>"
git tag design-freeze/v1
git push && git push --tags
```

## After the freeze
Announce it plainly to the human: from this commit, the specs are law. They change only via `/change-scope`. Downstream, ambiguity escalates — it is never guessed — and the escalation rate is now the design-quality signal. Next: `/preflight-audit` after issues and handover are generated.

## Profile note
For the `service-api` profile, Steps 3, 4 and 9 are N-A: `views.md`, the Step-4 render baselines, and the mock gate are **not** preconditions and there is no `baselines/` archive step. The frozen-track set is then `PRD.md`, `api-frontend-reference.yaml` (the consumer↔endpoint mapping), `api-spec.yaml`, `erd.dbml`, and any `research/msd_*.md`; the pre-freeze intent check is the generated API playground plus contract examples. Everything else — `CONTEXT.md`, `POLICY.md`, the freeze checklist, the tag — is identical.

## Hard rule
Do not freeze with an open `[NEEDS CLARIFICATION]` marker in any frozen-track file, or with a POLICY.md that does not parse. A design frozen over an open question is not frozen.
