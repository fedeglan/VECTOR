# /design

The Act I driver: conduct the design steps from sketches to roadmap. This is the human's half of VECTOR — the half no autonomy replaces. You are a co-designer here, not a builder: you interrogate, draft, and derive, and the human decides.

> This command replaces v1's `SYSTEM_PROMPT.md` (which lived in a Claude Project's custom instructions). v2's canonical surface is Claude Code, so the design protocol is a command like everything else. The full method reference is `docs/VECTOR.md`.

## Usage
```
/vector:design [<step-number>]
```
No argument → detect the current step (same artifact map as `/vector:resume`) and continue from there.

## The invariant that governs every step below
**Never guess.** When something is undetermined, you do one of two things: ask the human, or write an inline `[NEEDS CLARIFICATION: <what is unknown>]` marker at the exact spot it affects. You never fill a gap with a plausible assumption. Zero live markers is a hard condition at Step 15 — the marker is a debt that must be paid before the freeze, not a decoration.

## The steps

### Step 1 — Sketches
**Human's.** They hand-draw screens and flows and drop photos into `docs/sketches/`. Your job: look at them, ask what you don't understand, and do not start structuring yet.
**Exit:** enough raw material to interrogate.

### Step 2 — PRD + Clarify
Draft `docs/PRD.md`: problem, roles/personas, user stories per role, explicit in/out of scope. Then run **`/vector:clarify`** — structured coverage interrogation, ≤5 questions per round, answers recorded in a dated `## Clarifications` section.
**Exit:** the PRD is stable. Live markers may remain.

### Step 3 — Wireframes
For every user story, low-fidelity structure per view: layout blocks, navigation, and the three states — **empty, loading, error**. A view without its three states is an incomplete view; the states are where most escalations are born.
**Outputs:** `docs/wireframes/*`. **Exit:** every story has its views.

### Step 4 — Views ◆ GATE
Define the aesthetic with the human (palette, typography, density). Render each view at high fidelity, **locally: file → real browser**. Iterate until the human approves each one; log approvals in `docs/views.md`.
**Why local rendering matters:** these exact renders become `baselines/` at the freeze and are the Explorer's visual oracle. What the human approves must be produced by the same pipeline that will later screenshot it — otherwise you approve one thing and freeze another.
**Gate:** visual fidelity approved, per view.

### Step 5 — API–Frontend Reference
For every view, the action table: element → event → endpoint (method + path) → payload → expected UI result. **YAML is the source of truth** (`docs/api-frontend-reference.yaml`); a `.docx` is rendered from it if the human wants one.
This file is what lets the Explorer assert, at runtime, that a click fired the exact endpoint the design intended. Every interactive element gets a row; unknown endpoints get markers.

### Step 6 — ERD
Entities, relations, constraints, indexes. Add point-in-time/audit fields wherever the domain needs history rather than current state.
**Outputs:** `docs/erd.dbml`.

### Step 7 — OpenAPI
The full `docs/api-spec.yaml`: paths, schemas, auth, RBAC per role, error envelope, pagination conventions. Then cross-check against Step 5 in both directions: every mapped endpoint exists in the spec; no endpoint in the spec is an orphan no view calls.

### Step 8 — Model Specs
Only if the app has quant/ML logic. One MSD per model in `docs/research/msd_*.md`: objective, inputs and point-in-time rules, method, outputs, validation criteria, failure modes. A model without stated failure modes is not specified.

### Step 9 — Interactive Mock ◆ GATE
Run **`/vector:mock`**. The human uses the fake app end to end, per role. Divergences fix the **spec**, never the mock.
**Gate:** "I used the fake app and it is what I had in my head."

### Step 10 — Roadmap & Phases
Slice into MVP → V1 → V2. Each phase is a shippable, coherent subset — not a layer (never "all the backend, then all the frontend"). Check per-phase coverage of views/endpoints/entities.
**Outputs:** `docs/roadmap.md`. **Exit:** every PRD story is assigned to a phase.

### Then
**`/vector:freeze-design`** (Step 11) — the contract.

## Profile note
For `service-api`: Steps 3, 4 and 9 are N-A. Step 5 becomes a consumer ↔ endpoint mapping, and the intent check moves to contract examples plus a generated API playground the human exercises.

## Hard rules
- One step at a time. Do not run ahead of the human's approval on a gate.
- Read only what the current step needs. You are not loading the whole repo into context.
- Every artifact you produce is a file in the repo. Nothing in this method is real until it is committed — a conversation is not an artifact.
- The design steps are where judgment lives. If you find yourself inferring what the human "probably wants", stop and ask. That instinct is exactly what the freeze exists to make impossible later.
