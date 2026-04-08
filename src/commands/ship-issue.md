# /ship-issue

Full gitflow pipeline: branch from DEV → implement → self-review → PR → wait for human → merge → cleanup → log.

This is the primary development command. One issue at a time, full traceability.

## Before you start

Read these files in full:
- CLAUDE.md — your law
- CONTEXT.md — project understanding
- SESSIONS.md — latest entry for continuity

Identify the issue to work on. If not specified by the human, pick the next issue in dependency order from `docs/GITHUB_ISSUES.md`.

## Execution pipeline

### Stage 1 — Branch

```bash
git checkout DEV
git pull origin DEV
git checkout -b feat/T<NNN>-<short-desc>
```

Branch naming:
- Features: `feat/T<NNN>-<short-desc>`
- Fixes: `fix/T<NNN>-<short-desc>`
- Chores/infra: `chore/T<NNN>-<short-desc>`

### Stage 2 — Implement (runs /solve-issue)

Follow the full `/solve-issue` protocol:
- Read the issue from `docs/GITHUB_ISSUES.md` (the issue text IS the prompt)
- Implement the issue completely
- Write and run all tests
- Do not open a PR yet

### Stage 3 — Self-review (runs /review-pr)

Follow the full `/review-pr` protocol against your own implementation:
- Run through every item on the review checklist
- If any blocker is found: fix it immediately and re-run the checklist from the top
- Repeat until the checklist passes completely

### Stage 4 — Commit and push

```bash
git add -A
git commit -m "feat(T<NNN>): <short description of what was implemented>"
git push origin feat/T<NNN>-<short-desc>
```

### Stage 5 — Open PR

Create a PR targeting the DEV branch with:
- Title: `T<NNN>I<N>: <issue title>`
- Body:
  - What was implemented
  - Which spec files it satisfies (with section references)
  - Confirmation that the internal review passed
  - How to test it manually
- Labels: same as the issue labels
- Add label `ready-for-human-review`

### Stage 6 — Wait for human

Tell the human:
> "PR #<N> is ready for review: <PR URL>
> Issue: T<NNN>I<N> — <title>
>
> How to test:
> <manual testing instructions>
>
> Approve and I'll merge, or request changes."

Wait for the human's response. If changes requested, fix and push to the same branch. Re-run self-review.

### Stage 7 — Merge and cleanup

After human approves:

```bash
# Merge PR (squash or merge commit per project convention)
gh pr merge <PR-number> --merge --delete-branch

# Checkout DEV and pull
git checkout DEV
git pull origin DEV
```

### Stage 8 — Mark issue as done

```bash
# Close the GitHub issue with PR link
gh issue close <issue-number> --reason completed --comment "Completed in PR #<PR-number>"
```

### Stage 9 — Log session

Append to `SESSIONS.md`:

```markdown
### T<NNN>I<N>: <title>
- **PR**: #<PR-number>
- **Status**: ✅ Merged
- **Files changed**: <list>
- **Tests**: <N> passing
- **Notes**: <any decisions made or deviations from spec>
```

If this is the last issue of a coding session, also write the full session summary block.

## What a blocked pipeline looks like

If Stage 2 hits a blocker that cannot be resolved without a human decision:
- Do not open a PR
- Write a comment on the GitHub issue: `BLOCKED — <exact description of what is unclear and what decision is needed>`
- Log the blocker in SESSIONS.md
- Stop and tell the human

Do not guess. Do not make assumptions not supported by CLAUDE.md, CONTEXT.md, or the spec files.