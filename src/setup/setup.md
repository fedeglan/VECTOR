# /setup

Configure VECTOR on this machine. Run this once after cloning the repo.

## What you do — step by step

### 1. Locate the VECTOR repo
Find the directory containing `src/setup/SYSTEM_PROMPT.md` within the
allowed filesystem paths. Store this as `VECTOR_PATH`.

### 2. Ask for the projects folder
Ask the human:
> "Where do you want to store your projects? For example: /Users/you/Documents/Local-Projects"

Store the answer as `PROJECTS_PATH`.

### 3. Check for an existing config
Read `~/Library/Application Support/Claude/claude_desktop_config.json`.
If it does not exist, create it with `{}` first.

### 4. Check if already configured
If both `filesystem` and `github` already exist under `mcpServers`, tell the human:
> "VECTOR is already configured. You can start with `/new-project`."
And stop.

### 5. Configure the filesystem MCP
Add or update the `filesystem` entry in `mcpServers`:

```json
"filesystem": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "<PROJECTS_PATH>"
  ]
}
```

### 6. Set up the GitHub token securely via environment variable
Tell the human exactly this:

> "To connect to GitHub securely, I need a Personal Access Token. I'll store it
> as a system environment variable — it will never appear in any file or chat again
> after this step.
>
> **Step 1 — Generate the token:**
> Open this URL: https://github.com/settings/tokens/new
> - Name: VECTOR
> - Expiration: No expiration (or your preference)
> - Scopes: ✓ repo  ✓ read:user
> - Click 'Generate token' and copy it
>
> **Step 2 — Run this line in your terminal** (paste your token in place of `ghp_xxxx`):
> ```bash
> echo 'export GITHUB_TOKEN=ghp_xxxx' >> ~/.zshrc && source ~/.zshrc
> ```
> If you use bash instead of zsh, replace `~/.zshrc` with `~/.bash_profile`.
>
> **That's it.** The token lives in your system, not in any file Claude can read.
> Tell me when you've done it."

Wait for the human to confirm.

### 7. Configure the GitHub MCP using the environment variable
Add or update the `github` entry in `mcpServers`:

```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
  }
}
```

The token is never written to any file — the config only references the
environment variable name.

### 8. Write the final config
Merge the new `mcpServers` entries into the existing config object and write
the file back to `~/Library/Application Support/Claude/claude_desktop_config.json`.
Preserve all existing keys — do not overwrite the full file.

### 9. Confirm to the human
Tell the human:

> "✓ Filesystem MCP configured → <PROJECTS_PATH>
> ✓ GitHub MCP configured (token stored securely as environment variable)
>
> One last step: restart Claude Desktop for the changes to take effect.
>
> Once restarted, type:
>   /new-project <PROJECTS_PATH>/<your-project-name>"
