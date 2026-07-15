# /setup

Configure VECTOR on this machine. Run once. In v2 there is no Claude Project and no filesystem MCP to configure — Claude Code is the canonical surface and already has what it needs. This command installs the method, the runner, and the tooling the gates depend on, then proves it works.

## What you do — step by step

### 1. Confirm the plugin is installed
The human should already have run:
```
/plugin marketplace add fedeglan/vector
/plugin install vector
```
Verify the `/vector:*` commands resolve. If they do not, offer the fallback:
```bash
git clone https://github.com/fedeglan/vector.git && cd vector && make install
```
Report which install path is in use and the `method_version` — projects pin it at their freeze.

### 2. Install the Tier-2 runner
Install the built runner: `make runner` (or `pip install ./src/orchestration/runner`) — it exposes `vector-run start|resume|status|halt` and `vector-revert <tag>`. Its control flow is executed **39/39** against the real runner (`src/orchestration/runner/tests/test_fsm_live.py`, incl. a real SIGKILL/resume) with `fsm_sim.py` (the spec) still 8/8.

Tell the human plainly: the runner is **built and control-flow-proven, but not yet run with live `claude -p` builder processes** (that needs an authenticated headless CLI + a dedicated machine user for autonomous merges — see `src/orchestration/runner/README.md`). Until they set those up, **Act I and the gates are fully usable, and Act II is operated at L0/L1** — they drive `/ship-issue` per issue and merge each PR themselves, with the hooks and CI enforcing the contract underneath.

### 3. Install the Explorer's engine
```bash
npx playwright install --with-deps chromium
```
Playwright drives the autonomous exploratory pass (network interception + screenshots). Claude in Chrome is not a substitute here — it stays the human's interactive tool for `/vector:how-to-navigate`.

### 4. Verify Python
The hooks are portable `python3` (no jq dependency — macOS ships without it):
```bash
python3 --version        # 3.11+
```

### 5. GitHub: your account
```bash
gh auth status           # if not authenticated: gh auth login
```

### 6. GitHub: the machine user (required before any autonomous merge)
Autonomous merges must not run as the human — that is what makes branch protection meaningful. Tell the human exactly this:

> "Autonomous merges need a dedicated GitHub machine user — a separate account with
> least privilege on your project repos. This is what makes the gates real: *you* can't
> accidentally be the one merging past a red check, and the audit trail shows exactly
> which merges were the machine's.
>
> **Step 1 — Create the account:** a new GitHub account (e.g. `<you>-vector-bot`), added
> as a collaborator on the project repo with write access only.
>
> **Step 2 — Generate its token:** https://github.com/settings/tokens/new
> - Name: VECTOR runner
> - Scopes: ✓ repo
>
> **Step 3 — Store it as an environment variable** (never in a file, never in chat):
> ```bash
> echo 'export VECTOR_BOT_TOKEN=ghp_xxxx' >> ~/.zshrc && source ~/.zshrc
> ```
> Replace `~/.zshrc` with `~/.bash_profile` if you use bash.
>
> Tell me when that's done. This is only needed before the freeze — Act I design works
> without it."

Wait for confirmation. Never ask for the token itself, never read it, never write it anywhere.

### 7. Optional: the notification hook
If the human wants escalation/digest pings:
```bash
echo 'export TELEGRAM_BOT_TOKEN=...' >> ~/.zshrc
echo 'export TELEGRAM_CHAT_ID=...'   >> ~/.zshrc && source ~/.zshrc
```
One-way only. Recipients (single chat, list, or group) are set per project in `POLICY.md §12`.

### 8. Prove the gates work
Run the hook batteries from the installed plugin's reference copy. Resolve the plugin root first —
`$CLAUDE_PLUGIN_ROOT` is set inside Claude Code; for the `make install` fallback, `cd` into the
cloned `vector/` repo and use `.`:
```bash
PLUGIN="${CLAUDE_PLUGIN_ROOT:-.}"
python3 "$PLUGIN"/src/orchestration/hooks/tests/redteam.py
python3 "$PLUGIN"/src/orchestration/hooks/tests/redteam2.py
python3 "$PLUGIN"/src/orchestration/hooks/tests/redteam3.py
```
All three must pass. This is the same battery every project re-runs in its own repo at Step 15 — a green result here proves the machine's Python and the hook logic are sound before any project depends on them.

### 9. Confirm to the human

```
✓ VECTOR <method_version> installed (<plugin | make install>)
✓ Runner installed          → vector-run built (39/39); live-builder loop unproven, operate L0/L1
✓ Playwright installed      → the Explorer can drive a real browser
✓ GitHub authenticated      → <username>
<✓|—> Machine user token     → required before the design freeze
<✓|—> Notifications          → optional
✓ Hook batteries green      → the gates hold on this machine

Start a project:
  /vector:new-project /path/to/projects/<your-project-name>
```

## Hard rules
- Never ask for, read, or store a token in any file. Environment variables only.
- Do not skip step 8. A method whose gates were never executed on this machine is a claim, not a system.
