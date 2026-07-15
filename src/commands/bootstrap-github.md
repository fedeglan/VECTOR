# /bootstrap-github

Execute **Step 14 — Bootstrap & Protection**. Turn `.vector/issues.json` (the ledger from
Step 12) into a live GitHub Project **and stand up the gates that make autonomy safe**: branch
protection with the required checks, the escalation labels, and a machine-user identity that is
provably not you. Runs after `/handover` (Step 13), before `/preflight-audit` (Step 15).

> **Owner: the machine user.** This command runs authenticated as the dedicated machine user —
> not the human. That is what makes branch protection meaningful: *you* can never be the account
> that merged past a red check. Verify the identity first (Step 0). Source of truth is
> `.vector/issues.json`; `docs/GITHUB_ISSUES.md` is its human mirror.

## Before you start
Read `CLAUDE.md`, `CONTEXT.md`, `.vector/issues.json`, `docs/GITHUB_ISSUES.md`. Identify the repo
(`git remote -v`), the phases and their date ranges, and the machine-user handle from
`POLICY.md §6` (`bot_identity`).

### Step 0 — Verify the machine-user identity (do this first; abort if wrong)
```bash
ACTIVE=$(gh api user --jq .login)
BOT="<machine-user from POLICY.md bot_identity>"
[ "$ACTIVE" = "$BOT" ] || { echo "ABORT: gh is authenticated as '$ACTIVE', not the machine user '$BOT'. Autonomous merges must not run as the human."; exit 1; }
OWNER_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
PERM=$(gh api "repos/$OWNER_REPO/collaborators/$BOT/permission" --jq .permission)
echo "machine user '$BOT' permission on $OWNER_REPO: $PERM"
```
**Least-privilege vs. one-time admin (the reconciliation).** The machine user's steady-state
privilege is **write** (push) — that is all the runner needs to open PRs and merge through the
gates, and it is what keeps branch protection meaningful (the bot can't reconfigure the gates it
runs under). But *setting and reading* branch protection (Steps 6–7) is a repo-**admin** operation.
So run Steps 6–7 **once** under an admin identity — the human, or the machine user temporarily
granted admin just for bootstrap — then drop the machine user back to write for the ongoing loop.
Do not try to set or verify protection as a write-only user: it returns 403. If bootstrapping as
the human, still confirm the *runner's* future identity is the write-only `bot_identity`.

## Execution

### Step 1 — Create labels (incl. the escalation labels)
```bash
# Phase
gh label create "phase:mvp" --color "0E8A16" --description "MVP phase" 2>/dev/null || true
gh label create "phase:v1"  --color "1D76DB" --description "V1 phase"  2>/dev/null || true
gh label create "phase:v2"  --color "5319E7" --description "V2 phase"  2>/dev/null || true
# Type
for t in "feat:A2EEEF:Feature" "fix:D73A4A:Bug fix" "chore:FEF2C0:Chore" "infra:F9D0C4:Infrastructure" "review:C5DEF5:Review task"; do
  n=${t%%:*}; rest=${t#*:}; c=${rest%%:*}; d=${rest#*:}; gh label create "type:$n" --color "$c" --description "$d" 2>/dev/null || true; done
# Model
gh label create "model:haiku"  --color "BFD4F2" --description "Haiku"  2>/dev/null || true
gh label create "model:sonnet" --color "0075CA" --description "Sonnet" 2>/dev/null || true
gh label create "model:opus"   --color "B60205" --description "Opus"   2>/dev/null || true
# Complexity
gh label create "complexity:low"    --color "0E8A16" --description "Low"    2>/dev/null || true
gh label create "complexity:medium" --color "FBCA04" --description "Medium" 2>/dev/null || true
gh label create "complexity:high"   --color "D93F0B" --description "High"   2>/dev/null || true
# Escalation / human-attention (NEW in v2 — the runner applies these)
gh label create "needs-human" --color "B60205" --description "Parked; a human decision is required" 2>/dev/null || true
gh label create "escalated"   --color "E99695" --description "Escalation open (see ESCALATIONS.md)" 2>/dev/null || true
```

### Step 2 — Milestones (per phase, dated from the roadmap)
```bash
gh api repos/{owner}/{repo}/milestones -f title="MVP" -f due_on="<MVP end>T23:59:59Z" 2>/dev/null || true
gh api repos/{owner}/{repo}/milestones -f title="V1"  -f due_on="<V1 end>T23:59:59Z"  2>/dev/null || true
gh api repos/{owner}/{repo}/milestones -f title="V2"  -f due_on="<V2 end>T23:59:59Z"  2>/dev/null || true
```

### Step 3 — Project board
Capture the project number (Step 4 needs it) and create the Start/End **DATE** fields — a fresh
Projects v2 board has none, so writing dates without creating them fails. Needs the token's
`project` scope (`gh auth refresh -s project` if missing).
```bash
PROJ=$(gh project create --owner @me --title "<Project> — Development" --format json --jq .number)
gh project field-create "$PROJ" --owner @me --name "Start" --data-type DATE
gh project field-create "$PROJ" --owner @me --name "End"   --data-type DATE
# Status field options: Backlog / In Progress / In Review / Done (all issues start Backlog)
```

### Step 4 — Create issues FROM THE LEDGER
Iterate `.vector/issues.json` (authoritative), not the Markdown. For each issue create it with
title `T<NNN>I<N>: <title>`, the four labels, the milestone, and the body from
`docs/GITHUB_ISSUES.md`; then add it to the board and set its start/end dates. Preserve the id →
issue-number mapping (write it back into `.vector/issues.json` as `gh_number` so the runner can
find each issue). Batch with a 1s delay; pause 10s every 30 issues; on 429/403 wait 60s and retry.

### Step 5 — DEV branch
```bash
git checkout -b DEV && git push origin DEV
```

### Step 6 — Branch protection with the required checks (the point of the whole step)
Protect `DEV` so a merge is **mechanically impossible** until all six checks are green. The check
names must match the workflow job names from `/handover` exactly. **Use a typed JSON body** (`--input`),
NOT `-f` fields: the protection API requires real booleans/integers/null, and `-f` sends everything as
strings, which fails with a 422 (`"true" is not a boolean`).
```bash
gh api -X PUT "repos/$OWNER_REPO/branches/DEV/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["ci-tests","conformance","security","coverage-ratchet","test-protection","reviewer-approval"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0, "require_code_owner_reviews": true },
  "restrictions": null
}
JSON
```
> **Plan note:** classic branch protection (and the newer rulesets API) on a **private** repo requires
> GitHub Pro/Team; on the free plan it returns `403 Upgrade to GitHub Pro or make this repository public`.
> If the project repo is private on a free plan, either upgrade or the human makes it public; otherwise the
> merge-gate cannot be enforced and this is a Step-14 blocker, not something to skip silently.
- `require_code_owner_reviews=true` makes `CODEOWNERS` bite: a PR touching a frozen path needs the
  human's review even though ordinary PRs need zero human approvals (autonomy).
- `enforce_admins=true` so even an admin cannot merge past a red check.

### Step 7 — Self-verifying asserts against the ledger
The board must be provably consistent with `.vector/issues.json`. Assert, do not eyeball:
```bash
LEDGER=$(python3 -c "import json;print(len(json.load(open('.vector/issues.json'))['issues']))")
# --limit is REQUIRED: gh issue list defaults to 30, so without it CREATED caps at 30 and this
# assert aborts on any real multi-phase project (>30 issues) even when the board is correct.
CREATED=$(gh issue list --state all --limit 10000 --json number --jq length)
[ "$LEDGER" = "$CREATED" ] || { echo "ABORT: ledger has $LEDGER issues, GitHub has $CREATED"; exit 1; }
for p in mvp v1 v2; do
  L=$(python3 -c "import json;print(sum(1 for i in json.load(open('.vector/issues.json'))['issues'] if i['phase']=='$p'))")
  G=$(gh issue list --label "phase:$p" --state all --limit 10000 --json number --jq length)
  [ "$L" = "$G" ] || echo "PHASE MISMATCH $p: ledger $L vs GitHub $G"
done
# Branch protection is actually on, with all six contexts:
gh api "repos/$OWNER_REPO/branches/DEV/protection/required_status_checks" \
  --jq '.contexts' | tr ',' '\n' | grep -c -E 'ci-tests|conformance|security|coverage-ratchet|test-protection|reviewer-approval'  # expect 6
```

### Step 8 — Report
Write a local completion marker so `/vector:resume` can detect Step 14 without querying remote
GitHub state (its file-name scan cannot see "branch protection live"):
```bash
mkdir -p .vector && echo "bootstrapped $(date -u +%FT%TZ)" > .vector/bootstrap-complete
```
```
✓ GitHub bootstrapped as machine user <bot>  (permission: write)
✓ Issues: <N> created, provably matching the ledger (MVP <a> / V1 <b> / V2 <c>)
✓ Labels incl. needs-human / escalated; milestones; project board (Backlog→Done)
✓ DEV branch protected — required checks: ci-tests, conformance, security, coverage-ratchet, test-protection, reviewer-approval
✓ CODEOWNERS enforced on frozen paths (require_code_owner_reviews)
Log Session 0 in SESSIONS.md. Next: /preflight-audit (Step 15).
```

## Error handling
- `gh` not installed → `brew install gh` then re-auth **as the machine user**.
- Label/milestone exists → skip (handled above).
- Issue create fails → log, continue, report failures at the end; Step 7 will catch a count drift.
- Branch protection needs admin on the repo — if the machine user lacks it, the **human** applies
  the protection once (it is a one-time repo setting, not a per-merge action); the machine user
  operates under it thereafter. Say so rather than silently skipping protection.

## Hard rules
- Never run this as the human. If Step 0 shows the human's login, abort.
- Never report the board as ready if Step 7's asserts did not pass. A board that disagrees with the
  ledger is worse than no board — the runner would build against a lie.
- Branch protection is not optional. A repo without the required checks live is not at Step 14.
