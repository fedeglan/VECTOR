# /new-project

Create a new project scaffold and GitHub repo from scratch.

## Usage
```
/new-project /path/to/projects/<project-name>
```

## What you do — step by step

### 1. Parse the path
Extract:
- `PROJECT_PATH` — the full path provided by the human
- `PROJECT_NAME` — the last segment of that path
- `VECTOR_PATH` — locate the VECTOR repo by finding a directory containing
  `src/setup/SYSTEM_PROMPT.md` within the allowed filesystem

### 2. Check if the project already exists
Run `list_directory` on the parent of `PROJECT_PATH`.

If `PROJECT_NAME` already exists:
- Stop immediately.
- Tell the human: "A folder named `<project-name>` already exists at `<path>`. Did you mean `/resume <project-path>`?"

### 3. Create the local folder structure
Create directories one at a time, in this exact order.
Wait for each call to succeed before making the next one.

```
1.  <PROJECT_PATH>
2.  <PROJECT_PATH>/.claude
3.  <PROJECT_PATH>/.claude/commands
4.  <PROJECT_PATH>/docs
5.  <PROJECT_PATH>/docs/adrs
6.  <PROJECT_PATH>/docs/research
7.  <PROJECT_PATH>/docs/audits
8.  <PROJECT_PATH>/research
9.  <PROJECT_PATH>/backend
10. <PROJECT_PATH>/frontend
```

Do not batch these. Create them sequentially.

### 4. Copy VECTOR commands into the project
Copy each file individually from `<VECTOR_PATH>/src/commands/` to `<PROJECT_PATH>/.claude/commands/`.
Copy one file per call. Do not batch.

Files to copy:
- audit-plan.md
- bootstrap-github.md
- change-scope.md
- debug.md
- review-pr.md
- ship-issue.md
- solve-issue.md
- system-up.md

### 5. Write .gitignore
Write this content to `<PROJECT_PATH>/.gitignore`:

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

# OS
.DS_Store

# IDE
.vscode/
.idea/

# Docker
*.log
```

### 6. Write LICENSE
Write this content to `<PROJECT_PATH>/LICENSE`:

```
MIT License

Copyright (c) <year> <project-name>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

### 7. Create the GitHub repo
Use the GitHub MCP to create a new **private** repository named `<project-name>`
under the authenticated user's account.

If the repo already exists on GitHub, skip creation and use the existing remote URL.

### 8. Verify the result
Run `list_directory` on `<PROJECT_PATH>` and `<PROJECT_PATH>/.claude/commands/`
to confirm everything was created correctly.

### 9. Report to the human

```
✓ Project created at <PROJECT_PATH>
✓ Folders created
✓ VECTOR commands copied to .claude/commands/
✓ GitHub repo created at https://github.com/<username>/<project-name>

To finish setup, run these two commands in your terminal:

  cd <PROJECT_PATH>
  git init && git add . && git commit -m "init: vector project scaffold" && git remote add origin https://github.com/<username>/<project-name>.git && git push -u origin main

Then come back and type:
  /resume <PROJECT_PATH>
```