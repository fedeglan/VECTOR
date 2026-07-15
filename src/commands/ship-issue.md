# /ship-issue

Full per-issue pipeline: branch → implement → self-review → PR → gates → merge → tag → log. In v2 this runs **headless**, one issue per fresh process, driven by the relay-runner. It does not wait for a human — it either merges through the gates or escalates.

> Autonomy note: at L0/L1 the human still merges (this command stops at the PR and records the reviewer's shadow verdict). At L2/L3 the runner merges through the gates. The command is the same; POLICY decides who pulls the merge trigger.

## Before you start
Read `CLAUDE.md`, `CONTEXT.md`, the issue (its text is your prompt), and the spec section(s) it references. You are a fresh context — everything you need is in these.

## Pipeline

### 1. Branch
```bash
git checkout DEV && git pull origin DEV
git checkout -b feat/T<NNN>-<slug>    # or fix/ or chore/
```

### 2. Implement (the /solve-issue protocol)
Implement the issue completely — no more, no less. Match specs exactly. Write tests for everything (happy + error per endpoint; range/null/failure for quant). Run the issue's `verification:` block and the suite; all must pass.

**If you hit ambiguity or a spec conflict:** stop. Do not guess, do not work around it. Exit `blocked` with the exact decision needed as a question → the runner calls `/escalate`. A blocked exit is a correct outcome.

### 3. Self-review (the /review-pr checklist)
Run the full review checklist against your own diff. Fix any blocker and re-run from the top until clean.

### 4. Commit, push, PR
```bash
git add -A
git commit -m "feat(T<NNN>): <what was implemented>"
git push origin feat/T<NNN>-<slug>
```
Open a PR targeting DEV: what you built, which specs it satisfies (with section refs), how to test it. Labels = issue labels.

### 5. Gates
CI runs the required checks (ci-tests, conformance, security, coverage-ratchet, test-protection). Red → classify: a code/test failure is your problem (fix, within the 3-attempt budget); a CI-infra failure retries once then escalates `infra`. CI-red retries share the build-attempts budget.

### 6. Review + merge (runner-orchestrated)
A fresh reviewer process (paired tier) reviews the diff and sets the `reviewer-approval` status check. Then:
- **L0/L1:** stop here. Present the PR + reviewer verdict for the human to merge; the reviewer's verdict is recorded to `.vector/shadow.json` against the human's decision.
- **L2/L3:** with all required checks green, merge:
```bash
gh pr merge <N> --merge --delete-branch
git checkout DEV && git pull origin DEV
gh issue close <issue> --reason completed --comment "Completed in PR #<N>"
git tag -a vector/T<NNN>I<N> -m "merge T<NNN>I<N>"    # rollback handle
git push origin vector/T<NNN>I<N>                     # MUST push — an unpushed tag is not a rollback handle
```

### 7. Log
Append a deterministic entry to `SESSIONS.md` (issue, PR, files, tests, notes). Reset the consecutive-failure counter on a clean merge.

## Hard rules
- Never edit a frozen spec, delete/weaken a test, or add a dependency — the hooks block you, correctly. If the issue seems to need it, that's an escalation.
- Never guess. Blocked > wrong.
- Touch only the issue's files.
