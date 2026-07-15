# /explore

The Playwright Explorer: the autonomous exploratory-testing pass at phase close (Step 17, round-driven) and the smoke check every 10 merges. It walks the running app in a real browser, asserts that UI actions fire the exact endpoints the spec mapped, and diffs the visuals against the approved baselines.

## Engine
Playwright (CLI or MCP) — chosen because it intercepts network traffic cleanly and runs unattended. Claude in Chrome is deliberately **not** used here (interactive prompts, real profile, no clean interception); it stays the human's tool via `/how-to-navigate`.

## Rounds

### Round 1 — Happy paths, per role
For every row of `docs/api-frontend-reference.yaml`, as each role:
- Perform the UI action.
- **Intercept the network request and assert the exact endpoint + method fired** matches the reference. A wrong or missing call is a **P1** — this is the core check the mapping exists to enable.
- Assert a sane UI response (the expected result from the reference).

### Round 2 — Edge battery
Empty states, invalid form input, refresh mid-flow, browser back/forward, session expiry, double-submit, unauthorized access attempts per role.

### Round 3 — Changed surface
The views flagged by this phase's merged PRs (via the `CONTEXT.md` module map) — re-walk them specifically.

### Round 4 — Visual + a11y
Screenshot at 3 viewports; diff against `baselines/` per POLICY thresholds (MVP functional-only; V1+ ≥2% area = P3). Run the a11y pass (AA informational in MVP).

## Output
Every finding → `docs/testing/BUG_BACKLOG.md` in exact `/report-bug` format, with severity by rubric and **a screenshot + the intercepted network log attached**:
- **P0** — a user flow is broken.
- **P1** — wrong or failed endpoint call.
- **P2** — state or UX anomaly.
- **P3** — visual diff over threshold.

## Smoke mode
Every 10 merges, run rounds 1 and 3 only — fast drift detection without the full battery.

## Profile note
The rounds above are the `webapp` profile. For `service-api` (Steps 3, 4, 9 N-A — no views, no baselines), the Explorer swaps to **API-level probing**: schemathesis against `docs/api-spec.yaml` plus scenario contract tests against staging, keeping Round 1's core check (assert each mapped consumer↔endpoint call fires with the right method and a sane response) and Round 2's edge battery (auth per role, invalid payloads, pagination, error envelopes). Rounds 3–4 (changed views, visual + a11y diff vs `baselines/`) drop out. Findings still land in `docs/testing/BUG_BACKLOG.md` by the same severity rubric.

## Hard rule
Report what you observe; do not fix here. Fixes are `/fix-bugs`, which routes by severity and sends each fix back through the full build gate.
