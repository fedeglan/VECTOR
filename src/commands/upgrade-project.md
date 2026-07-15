# /upgrade-project

Retrofit an existing VECTOR v1 project (or a compatible repo) to the v2 contract: install the enforcement layer, write POLICY.md, and wire the gates — without touching the frozen design or the code. This is the one brownfield path v2 supports.

## Preconditions
- The project has VECTOR v1 structure (`CLAUDE.md`, `CONTEXT.md`, `docs/` specs) or an equivalent design-frozen state.
- A dedicated GitHub machine user is available for autonomous merges.

## What you do

### 1. Assess
Read the project's specs and `CONTEXT.md`. Identify: the frozen-track artifacts present, the stack, and which VECTOR profile fits (`webapp` | `service-api`). Report what is present and what is missing before changing anything.

### 2. Instantiate POLICY.md
Create it with the human (autonomy level, budgets, breakers, deploy target, notify recipients, `method_version` pin). Recommend starting at **L1** for a retrofitted project regardless of the author's usual default — the shadow-mode telemetry has to be earned on this codebase.

### 3. Install the enforcement layer (files only — copy the producers, not just the consumers)
Copy from the installed plugin (`$CLAUDE_PLUGIN_ROOT`, or the cloned `vector/` repo). A workflow
that invokes a script you did not install is a red check on every PR, so **install the producers**:
```bash
PLUGIN="${CLAUDE_PLUGIN_ROOT:-.}"
mkdir -p .claude/hooks/tests .github/workflows .github/scripts
# edit-time hooks + their regression suite (the batteries Step 5's preflight re-runs in-repo)
cp "$PLUGIN"/src/orchestration/hooks/{frozen_specs,test_protection,deps_guard}.py .claude/hooks/
cp "$PLUGIN"/src/orchestration/hooks/tests/{redteam,redteam2,redteam3}.py .claude/hooks/tests/
# merge-time CI: the two logic nets (verbatim) + the workflow templates (ADAPT to this stack)
cp "$PLUGIN"/src/orchestration/ci/{coverage_ratchet,test_protection_ci}.py .github/scripts/
cp "$PLUGIN"/src/templates/workflows/*.yml .github/workflows/
# CODEOWNERS — substitute the human's handle and verify no placeholder remains
sed "s/{{HUMAN_GITHUB_USER}}/<human-github-handle>/g" "$PLUGIN"/src/templates/CODEOWNERS > CODEOWNERS
grep -q '{{HUMAN_GITHUB_USER}}' CODEOWNERS && echo "ERROR: CODEOWNERS placeholder unreplaced" || true
```
- Wire the three hooks in `.claude/settings.json` (matcher `Edit|Write|MultiEdit|NotebookEdit|Bash`);
  no read-side deny-rules (writes are hooked, reads stay open for the reviewer).
- **Adapt each workflow** to the existing stack, keeping each job name == its required-check name; a
  `service-api` project drops the frontend steps. Provide `conformance.yml`'s project-specific
  migrations↔ERD step (`.github/scripts/erd_diff.*`) as `/handover` describes.
- **Initialize the coverage baseline** (committed, or `coverage-ratchet` fails as missing):
  `pytest … --cov --cov-report=xml || true; [ -f coverage.xml ] && python3 .github/scripts/coverage_ratchet.py --coverage-xml coverage.xml --baseline .vector/coverage-baseline --set-baseline || echo 0.0 > .vector/coverage-baseline`.
- `.vector/` skeleton, `ESCALATIONS.md`, the ops-pack skeleton.

### 4. Bootstrap protection
Branch protection on DEV with the required checks; verify the machine user; set the `reviewer-approval` status check.

### 5. Preflight
Run `/preflight-audit`. A retrofitted repo often surfaces coverage gaps (endpoints with no issue, specs with drift) — these are findings to resolve before autonomy, exactly as in a fresh project.

## Hard rules
- Do not modify the existing frozen specs or the application code. This command adds enforcement; it does not redesign.
- If the existing specs are not actually consistent (v1 drift), report it — the human resolves via `/change-scope`. Do not silently "fix" a spec to make the matrix pass.
- The project does not go autonomous until `/preflight-audit` is green.
