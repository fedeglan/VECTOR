# /test-plan

Audit the test suite, complete it, execute all layers, and classify every failure. Runs in two modes: **fast** (during the build loop and at the top of phase close) and **thorough** (the final gate before phase acceptance). In v2 the classification of failures is what makes it safe to run autonomously.

## Layers
- Unit — every function/service.
- Integration — endpoints against a real test DB (from the deterministic seed).
- Contract — conformance to `api-spec.yaml` (schemathesis) and migrations vs `erd.dbml`.
- Quant (if applicable) — range, null handling, known failure modes per MSD.

## Fast vs thorough
- **Fast:** unit + integration + contract, fail-fast, for quick signal.
- **Thorough:** all layers, full run, no fail-fast — the acceptance gate.

## Failure classification (the safety mechanism)
Every failure is classified before any fix:
- **code-bug** → the code is wrong. Auto `/debug`, fix, and add a mandatory regression test. Back through the build gate.
- **test-bug** → the test is wrong. Fix it **only with a justification block + reviewer sign-off on the delta** (the hooks and CI test-protection enforce this — you cannot quietly weaken a test).
- **flaky** → non-deterministic. Retry ×2; if still flaky, quarantine it and auto-file an issue. Never delete it.
- **spec-conflict** → the test encodes one spec, the code satisfies another. Do **not** pick a side. Escalate.

## Coverage
Fill genuine gaps (untested functions, endpoints, components). Adding tests is always allowed; the ratchet ensures coverage never drops. Do not pad coverage with hollow tests — the reviewer treats those as blockers.

## Output
A report: layers run, pass/fail counts, each failure with its classification and resolution, coverage delta. In thorough mode, a regression here sends the phase back to `/fix-bugs`.

## Hard rules
- Never weaken or delete a test to make the suite green. A red test is either a code-bug (fix the code), a test-bug (fix the test with sign-off), flaky (quarantine), or a spec-conflict (escalate). There is no fifth option.
- Never resolve a spec-conflict by editing the test to match the code, or vice versa. Escalate.
