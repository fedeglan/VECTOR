# /new-project

Scaffold a new VECTOR project: the repo skeleton, the project-level `.claude/`, the enforcement-layer wiring, and the GitHub repo. This instantiates the **contract side** of VECTOR; the **method side** is already on the machine via the installed plugin.

## Usage
```
/vector:new-project /path/to/projects/<project-name> [--profile webapp|service-api]
```

## What you do — step by step

### 1. Parse and check
Extract `PROJECT_PATH` (full path given by the human) and `PROJECT_NAME` (last segment). Run `list_directory` on the parent.

If `PROJECT_NAME` already exists:
- Stop immediately.
- Tell the human: "A folder named `<project-name>` already exists at `<path>`. Did you mean `/vector:resume <project-path>`?"

If `--profile` was not given, ask: `webapp` (fullstack, all 19 steps) or `service-api` (no views/mock; API-level exploration). Default `webapp`.

### 2. Create the local folder structure
Create directories one at a time, in this exact order. Wait for each to succeed.

```
1.  <PROJECT_PATH>
2.  <PROJECT_PATH>/.claude
3.  <PROJECT_PATH>/.claude/hooks
4.  <PROJECT_PATH>/.claude/hooks/tests
5.  <PROJECT_PATH>/.vector
6.  <PROJECT_PATH>/docs
7.  <PROJECT_PATH>/docs/sketches
8.  <PROJECT_PATH>/docs/wireframes
9.  <PROJECT_PATH>/docs/adrs
10. <PROJECT_PATH>/docs/research
11. <PROJECT_PATH>/docs/audits
12. <PROJECT_PATH>/docs/testing
13. <PROJECT_PATH>/baselines
14. <PROJECT_PATH>/ops
15. <PROJECT_PATH>/backend      (webapp | service-api)
16. <PROJECT_PATH>/frontend     (webapp only)
```

Do not batch these. Create them sequentially.

### 3. Install the enforcement layer
Copy from the installed plugin's `src/orchestration/hooks/` into `<PROJECT_PATH>/.claude/hooks/`:
- `frozen_specs.py`, `test_protection.py`, `deps_guard.py`
- `tests/redteam.py`, `tests/redteam2.py`, `tests/redteam3.py` (the project's own gate regression suite — Step 15 runs them in-repo)

Write `<PROJECT_PATH>/.claude/settings.json` wiring the three hooks on `PreToolUse` (matcher `Edit|Write|MultiEdit|NotebookEdit|Bash`, invoked as `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/<hook>.py"`). Use the plugin's `src/orchestration/hooks/hooks.json` as the reference. No read-side `permissions.deny` on frozen paths: the reviewer and builder must read the specs, and every write path is hooked regardless of how the file entered context.

**Do not copy the slash commands.** In v2 the commands resolve globally from the installed `vector` plugin as `/vector:*` (or from `~/.claude/` for a `make install` fallback). If the human expects a `.claude/commands/` full of files as in v1, explain: **the plugin owns the method; the repo owns the contract.**

### 4. Write the base files

`<PROJECT_PATH>/.gitignore`:
```
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
dist/
.env

# Node
node_modules/
.next/
dist/

# VECTOR
# (comments MUST be on their own line — git does not support trailing comments in .gitignore)
# mock/ is the disposable Step-9 prototype; state.json/digest/ are runtime state, not source
mock/
playground/
.vector/state.json
.vector/digest/
.vector/change-scope-open

# OS / IDE
.DS_Store
.vscode/
.idea/

# Docker
*.log
```

`<PROJECT_PATH>/LICENSE` — MIT, current year, `<project-name>`.
`<PROJECT_PATH>/README.md` — a stub: project name, one-line description, "built with VECTOR", and a note that the method and contract live in `docs/` + `POLICY.md`.

**Do not write `POLICY.md` here.** It is instantiated at the Design Freeze (Step 11), when its values are actually known. Never write a placeholder POLICY with invented values — the runner parses it fail-fast and invented defaults are exactly the kind of silent assumption this method exists to prevent.

### 5. Create the GitHub repo
Create a **private** repository named `<project-name>` under the authenticated account. If it already exists, skip creation and use the existing remote URL.

Note for later: autonomous merges (Step 14) require a **dedicated machine user** with least privilege. Flag it now so the human can create it before the freeze — it is not needed for Act I design.

### 6. Verify
Run `list_directory` on `<PROJECT_PATH>` and `<PROJECT_PATH>/.claude/hooks/` to confirm everything landed.

### 7. Report to the human

```
✓ Project created at <PROJECT_PATH>          (profile: <profile>)
✓ Folder structure created
✓ Enforcement hooks installed + wired in .claude/settings.json
✓ GitHub repo created at https://github.com/<username>/<project-name>
  Commands resolve from the vector plugin (/vector:*) — not vendored per project.

To finish setup, run these in your terminal:

  cd <PROJECT_PATH>
  git init && git add . && git commit -m "init: vector project scaffold" && git remote add origin https://github.com/<username>/<project-name>.git && git push -u origin main

Then we begin Act I — Design:
  Step 1: drop your sketches into docs/sketches/
  Step 2: we draft the PRD, then run /vector:clarify

Before the freeze (Step 11) you'll need a GitHub machine user for autonomous merges.
```

## Hard rules
- Commands are not vendored per project in v2 — the plugin owns them, versioned as a unit.
- `POLICY.md` is a freeze-time artifact. Do not scaffold it.
- Do not start designing here. This command creates the container; Act I fills it.
