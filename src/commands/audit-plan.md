# /audit-plan

Audit the codebase against the frozen plan and specs. Runs every 10 merges (drift check) and at the top of phase close (blocking gate). It answers one question: does what was built still match what was designed?

## What you check
- **Coverage:** every issue marked done has actually landed (merged PR, closed issue, code present). Every endpoint in `api-spec.yaml` for this phase exists; every entity has its migration.
- **Conformance drift:** the implemented endpoints still match the OpenAPI (this overlaps the conformance CI check — here you catch semantic drift the schema check can't, e.g. an endpoint that matches the schema but ignores a business rule from the PRD).
- **Architecture drift:** no forbidden pattern crept in across merges (layering, business logic in routers, cross-package imports the CONTEXT forbids).
- **Plan drift:** the roadmap phase still describes what's being built; nothing silently expanded scope.

## Output
A findings list. Each finding is one of:
- **blocker** — auto-file a fix issue into the current phase and route it back through the build loop.
- **spec-conflict** — the code and a spec genuinely disagree → escalate, don't resolve.
- **observation** — non-blocking, logged.

## Cadence behavior
- **Every 10 merges:** run the drift check; auto-file blockers; keep the loop moving.
- **Phase close:** blocking — the phase does not proceed to acceptance with an open blocker.

## Hard rules
- This is an audit, not a redesign. You report and route; you don't rewrite specs to match code.
- A blocker auto-files an issue — it does not get silently fixed inline outside the gated pipeline.
