# /mock

Generate a clickable interactive prototype (Step 9) from the frozen-track design artifacts, so the human can *use the fake application* before freezing the real one. This is the intent check — moved upstream to where corrections cost minutes instead of change-scopes.

## Inputs
- `docs/views.md` + the approved renders (Step 4)
- `docs/api-spec.yaml` (Step 7)
- `docs/api-frontend-reference.yaml` (Step 5)

## What you do

### 1. Generate — never hand-author
Build a disposable front-end prototype (Vite + a mock service worker, e.g. MSW) where:
- Each screen comes from the approved views.
- Every action-table row (element → event → endpoint) is wired to a **mocked** response whose shape is derived from the OpenAPI schema for that endpoint.
- Mock data comes from schema examples / seed-like fixtures — enough to make the app feel real per role.
- Role switching is available so the human can walk each persona's flows.

Put it in `mock/` (gitignored; it is disposable). Print the URL to open it.

### 2. Hand it to the human
Tell them: open the mock, use it end to end as each role, and note anything that feels wrong — a missing screen, a confusing flow, an action that should exist, a field that shouldn't.

### 3. Anti-drift rule — divergences fix the SPEC
This is the one rule that keeps the mock safe. The mock is **generated and disposable**; it is **never hand-edited**. When the human finds a divergence:
- Fix it in the upstream artifact — `views.md`, `api-frontend-reference.yaml`, `api-spec.yaml`, or `PRD.md`.
- Regenerate the mock from the corrected artifacts.
- Never patch the mock directly to "make it look right" — that would put intent outside the contract and create a second oracle.

### 4. Timebox
2–3 days maximum. If the mock is taking longer, it is being built too well — it is a prototype, not the product.

## Exit — the gate
The human confirms: **"I used the fake app and it is what I had in my head."** That confirmation is the gate. Only then does design proceed toward the freeze. If the human is not there yet, the divergences become spec fixes and you regenerate.

## Profile note
For the `service/api` profile this command is N-A; the intent check moves to contract examples plus a generated API playground the human exercises instead.
