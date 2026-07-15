# /escalate

File a decision request when the machine has hit something it must not resolve on its own. This is the *only* sanctioned response to ambiguity. Escalating is a correct outcome — guessing is a defect.

## When to escalate (the six classes)
- **spec-conflict** — the code cannot satisfy two frozen specs at once, or a spec is internally contradictory. The spec may be wrong, not the code.
- **ambiguity** — the issue does not determine what to build, and no spec resolves it.
- **budget** — build attempts (3), review cycles (2), issue time (60m), or run time (8h) exhausted.
- **infra** — CI infrastructure, auth, or environment failure that is not the code's fault.
- **security** — a credential-exposure, injection, or supply-chain risk surfaced mid-build.
- **review-deadlock** — third reviewer rejection on the same PR; builder and reviewer disagree.

## What you do
1. Write an entry to `ESCALATIONS.md`:
```markdown
## <ISO-datetime> — T<NNN>I<N> — <class>
**Decision needed:** <the exact question, phrased so a yes/no or a single choice unblocks it>
**Context:** <what was attempted; which specs/issues are involved>
**Options considered:** <if any, with the trade-off of each — but do NOT pick one>
**Blocked:** <this issue> · **Also blocked (dependents):** <T… list, or none>
**Independent work continuing:** <T… list, or none>
```
2. Label the GitHub issue `needs-human` and add a comment linking the escalation.
3. If a notification hook is configured, fire it (one-way).
4. **Park and continue:** the blocked issue and its dependents stop; independent DAG branches keep going. Do not halt the whole run unless this is freeze-class (critical security, or a spec-conflict blocking >50% of the remaining DAG).

## Hard rules
- Phrase the decision as a question. Do not resolve it, do not pick an option, do not implement a "temporary" workaround.
- A spec-conflict re-queues its issue only after the human runs `/change-scope` and the freeze marker is updated — enforced by timestamp.
- Ambiguity, review-deadlock, and spec-conflict escalations are design signals — they do **not** count toward the consecutive-failure breaker. Only budget/build failures do.
