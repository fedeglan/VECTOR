# /resume

Resume an existing VECTOR project. Detects where the project stands and loads only what the current step needs. In Act II, state on disk is authoritative — not inference.

## Usage
```
/vector:resume /path/to/projects/<project-name>
```

## What you do — step by step

### 1. Verify the project exists
Run `list_directory` on the provided path.

If the path does not exist:
- Stop immediately.
- Tell the human: "No project found at `<path>`. Did you mean `/vector:new-project <path>`?"

### 2. Check for runner state FIRST
If `<PROJECT_PATH>/.vector/state.json` exists, the project is in **Act II** and that file is authoritative — do not infer anything from artifacts. Read it plus `POLICY.md` and report:

```
Project: <name>          Profile: <profile>          Level: <autonomy_level>
Phase: <phase> — <N merged> / <M total> issues
Escalations open: <N>    (see ESCALATIONS.md)
Halted: <reason, or no>
Last activity: <from state.json>

Next action: /vector:run-phase to resume, or resolve the open escalations first.
```
If the run is halted by a breaker, say why and stop — the human decides. If escalations are open, list the exact decisions needed. Then stop; do not auto-resume the loop without the human.

### 3. Otherwise, detect the current step from artifacts
Run `list_directory` on `<PROJECT_PATH>/docs/` and the root — file names only, no content.

| Artefact exists | Step completed |
|---|---|
| Nothing in docs/ | Step 1 not started |
| docs/sketches/* | Step 1 |
| docs/PRD.md | Step 2 (check for a `## Clarifications` section — if absent, `/vector:clarify` is the next action) |
| docs/wireframes/* | Step 3 |
| docs/views.md | Step 4 |
| docs/api-frontend-reference.yaml | Step 5 |
| docs/erd.dbml | Step 6 |
| docs/api-spec.yaml | Step 7 |
| docs/research/msd_*.md (≥1, or N-A for this project) | Step 8 |
| mock/ exists or views.md logs the mock gate | Step 9 |
| docs/roadmap.md | Step 10 |
| CONTEXT.md + POLICY.md + git tag `design-freeze/v1` | **Step 11 — frozen** |
| docs/GITHUB_ISSUES.md + .vector/issues.json | Step 12 |
| CLAUDE.md + .github/workflows/ + CODEOWNERS | Step 13 |
| .vector/bootstrap-complete (marker written by /bootstrap-github; board + protection live) | Step 14 |
| docs/audits/preflight-*.md green | **Step 15 — authorized** |

Profile note: for `service-api`, Steps 3, 4 and 9 are N-A and are skipped in this map.

### 4. Check the freeze state
If `POLICY.md` exists, the design is frozen. Say so plainly, and remember it for the rest of the session: specs change only via `/vector:change-scope`; ambiguity escalates, never gets guessed.

### 5. Load only what the current step needs
Read only the artifacts the current step consumes. Do not read the whole repo.

### 6. Report to the human in exactly this format

```
Project: <project name>          Profile: <profile>
Repo: <project path>
Design: <in progress | FROZEN at <tag>, method_version <x.y.z>>

Completed steps: <list, or "none">
Current step: Step N — <step name>
Status: <one sentence on what was last completed>

Next action: <exactly what you are going to do now, or what you need from the human>
```

### 7. Execute or prompt
If you have everything needed to proceed, start immediately.
If you need input from the human, ask for it in one message — no more than two questions.

## Hard rule
Never infer Act II progress from artifacts when `.vector/state.json` exists. The ledger is the truth; the file tree is a shadow of it.
