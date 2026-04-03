# /resume

Resume an existing VECTOR project. Detects the current step automatically and loads only what is needed.

## Usage
```
/resume /path/to/projects/<project-name>
```

## What you do — step by step

### 1. Verify the project exists
Run `list_directory` on the provided path.

If the path does not exist:
- Stop immediately.
- Tell the human: "No project found at `<path>`. Did you mean `/new-project <path>`?"

### 2. Detect the current step
Run `list_directory` on `<PROJECT_PATH>/docs/` — file names only, no content.

Check for the presence of files using the artefact map:

| Artefact exists | Step completed |
|---|---|
| Nothing in /docs/ | Step 1 not started |
| Sketches referenced in session | Step 1 complete |
| docs/PRD.md | Step 2 complete |
| docs/views.md | Step 3 complete |
| /frontend/src/ has component files | Step 4 complete |
| docs/api-spec.yaml | Step 5 complete |
| docs/data-model.md + docs/erd.dbml | Step 6 complete |
| docs/research/msd_*.md (at least one) | Step 7 complete |
| docs/architecture.md | Step 8 complete |
| CLAUDE.md at root | Step 9 complete |
| CLAUDE.md contains "DESIGN FREEZE: YES" | Step 9.5 complete |
| docs/DEVELOPMENT_PLAN.md | Step 10 complete |
| docs/github_issues.md | Step 11 complete |

### 3. Load only what the current step needs
Read only the files listed in the `Reads:` field of the current step in the system prompt. Do not read anything else.

### 4. Report to the human in exactly this format

```
Project: <project name>
Repo: <project path>

Completed steps: <list, or "none">
Current step: Step N — <step name>
Status: <one sentence on what was last completed>

Next action: <exactly what you are going to do now, or what you need from the human>
```

### 5. Execute or prompt
If you have everything needed to proceed, start immediately.
If you need input from the human, ask for it in one message — no more than two questions.
