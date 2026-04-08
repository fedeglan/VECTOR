# /bootstrap-github

Convert `docs/GITHUB_ISSUES.md` into a live GitHub Project with all issues, labels, milestones, and dates.

This is the first command Claude Code runs when it takes over the project.

## Before you start

Read these files:
- CLAUDE.md — project conventions
- CONTEXT.md — project overview
- docs/GITHUB_ISSUES.md — the source of truth for all issues

Identify:
- The GitHub repo (from `git remote -v`)
- The total number of issues to create
- The phases and their date ranges

## Execution

### Step 1 — Create labels

Create these labels on the repo (skip any that already exist):

```bash
# Phase labels
gh label create "phase:mvp" --color "0E8A16" --description "MVP phase"
gh label create "phase:v1" --color "1D76DB" --description "V1 phase"
gh label create "phase:v2" --color "5319E7" --description "V2 phase"

# Type labels
gh label create "type:feat" --color "A2EEEF" --description "Feature"
gh label create "type:fix" --color "D73A4A" --description "Bug fix"
gh label create "type:chore" --color "FEF2C0" --description "Chore"
gh label create "type:infra" --color "F9D0C4" --description "Infrastructure"
gh label create "type:review" --color "C5DEF5" --description "Review task"

# Model labels
gh label create "model:haiku" --color "BFD4F2" --description "Haiku model"
gh label create "model:sonnet" --color "0075CA" --description "Sonnet model"
gh label create "model:opus" --color "B60205" --description "Opus model"

# Complexity labels
gh label create "complexity:low" --color "0E8A16" --description "Low complexity"
gh label create "complexity:medium" --color "FBCA04" --description "Medium complexity"
gh label create "complexity:high" --color "D93F0B" --description "High complexity"
```

### Step 2 — Create milestones

```bash
gh api repos/{owner}/{repo}/milestones -f title="MVP" -f description="Minimum viable product" -f due_on="<MVP end date>T23:59:59Z"
gh api repos/{owner}/{repo}/milestones -f title="V1" -f description="Full first version" -f due_on="<V1 end date>T23:59:59Z"
gh api repos/{owner}/{repo}/milestones -f title="V2" -f description="Post-V1 features" -f due_on="<V2 end date>T23:59:59Z"
```

### Step 3 — Create a GitHub Project

```bash
# Create the project
gh project create --owner @me --title "<Project Name> — Development" --format json

# Note the project number for later use
```

### Step 4 — Create all issues

Parse `docs/GITHUB_ISSUES.md` and create each issue in execution order.

For each issue in the document:

```bash
# Create the issue
gh issue create \
  --title "T<NNN>I<N>: <title>" \
  --body "<full issue body from GITHUB_ISSUES.md>" \
  --label "phase:<phase>,type:<type>,model:<model>,complexity:<level>" \
  --milestone "<MVP|V1|V2>"
```

After creating each issue, add it to the GitHub Project and set the start/end dates:

```bash
# Add to project and set dates
gh project item-add <project-number> --owner @me --url <issue-url>

# Set start and end dates on the project item
# Use the GitHub API to set date fields
gh api graphql -f query='
  mutation {
    updateProjectV2ItemFieldValue(input: {
      projectId: "<project-id>"
      itemId: "<item-id>"
      fieldId: "<start-date-field-id>"
      value: { date: "<YYYY-MM-DD>" }
    }) { projectV2Item { id } }
  }'
```

**Important:** The start date and end date for each issue come from the `**Start date**` and `**End date**` fields in GITHUB_ISSUES.md. These dates populate the GitHub Project's built-in timeline/Gantt view.

### Step 5 — Set up the Project board columns

Configure the project's Status field with these options:
- Backlog
- In Progress
- In Review
- Done

All issues start in "Backlog".

### Step 6 — Create DEV branch

```bash
git checkout -b DEV
git push origin DEV
```

### Step 7 — Verify

Run verification checks:

```bash
# Count issues created
CREATED=$(gh issue list --state all --json number --jq length)
echo "Issues created: $CREATED"

# Count by phase
echo "MVP: $(gh issue list --label 'phase:mvp' --state all --json number --jq length)"
echo "V1: $(gh issue list --label 'phase:v1' --state all --json number --jq length)"
echo "V2: $(gh issue list --label 'phase:v2' --state all --json number --jq length)"

# Verify milestones
gh api repos/{owner}/{repo}/milestones --jq '.[].title'

# Verify project exists
gh project list --owner @me
```

### Step 8 — Report

```
✓ GitHub Project bootstrapped

Issues created: <N> (MVP: <N>, V1: <N>, V2: <N>)
Milestones: MVP (<date>), V1 (<date>), V2 (<date>)
Project board: <project URL>
DEV branch: created and pushed

Labels applied: phase, type, model, complexity
Dates set: start and end dates on all project items

The project timeline/Gantt view is now populated.
Ready to start development with /ship-issue.
```

Log this in SESSIONS.md as Session 0.

## Error handling

- If `gh` CLI is not installed: `brew install gh` and `gh auth login`
- If label already exists: skip (gh will warn, not error)
- If milestone already exists: skip
- If issue creation fails: log the error, continue with next issue, report failures at the end
- If project date fields are not available: create them via the API first
- Rate limiting: if GitHub returns 429, wait and retry with exponential backoff

## Rate limiting strategy

GitHub API has rate limits. For large projects (100+ issues):
- Batch issue creation with 1-second delays between calls
- After every 30 issues, pause for 10 seconds
- If a 429 or 403 is received, wait 60 seconds and retry