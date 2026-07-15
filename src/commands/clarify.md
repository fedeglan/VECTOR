# /clarify

Structured, coverage-based interrogation of the PRD, run right after the first draft (Step 2). The point is to make ambiguity *visible* early — where a correction costs a sentence — instead of letting it surface downstream as an escalation or, worse, a wrong build.

## When
After a PRD draft exists and before wireframes. Re-run after any material scope change.

## What you do

### 1. Read the PRD and scan for coverage gaps
Walk these dimensions and find what the PRD does not yet determine:
- **Functional scope** — every user story has an actor, an action, and an outcome.
- **Roles & permissions** — who can do what; what each role cannot do.
- **Data lifecycle** — for each entity: created how, edited by whom, deleted/archived how, retained how long.
- **Edge cases & states** — empty, loading, error, partial, offline, concurrent.
- **Integrations** — external systems, auth providers, third-party APIs.
- **Non-functionals** — expected scale, latency, uptime, privacy/compliance constraints.

### 2. Ask — in rounds, ≤5 questions each
Ask the highest-leverage questions first. Prefer questions whose answer eliminates the most downstream ambiguity. One round at a time; wait for answers before the next.

### 3. Record answers
Append to a dated **Clarifications** section in `docs/PRD.md`:
```markdown
## Clarifications — <ISO-date>
- Q: <question> → <the human's answer>
```

### 4. Mark what stays open
Anything unresolved gets an inline **`[NEEDS CLARIFICATION: <what is unknown>]`** marker at the exact spot in the PRD it affects. This convention now governs every downstream artifact. Live markers are allowed to persist through design — but **zero live markers is a hard condition at Step 15 (preflight)**. Nothing freezes with an open question inside it.

## Hard rules
- Do not invent answers to your own questions. An unanswered question becomes a marker, not an assumption.
- Do not ask trivia; ask what changes the build. If the PRD already determines it, don't ask.
- Stop when the remaining unknowns are genuinely the human's open product decisions, not gaps you could have closed by reading.
