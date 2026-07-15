# /generate-issues

Execute **Step 12 — Issues & Ledger**. Turn the frozen design into the unit-of-work backlog:
`docs/GITHUB_ISSUES.md` (human-readable) and `.vector/issues.json` (the machine ledger the
relay-runner consumes). Runs **after the freeze (Step 11)**, before `/handover` (Step 13) and
`/bootstrap-github` (Step 14).

> Note: the relay-runner is built and consumes this ledger (`.vector/issues.json` → its ready-set)
> and writes `.vector/state.json`. Until its live `claude -p` builder loop is exercised (needs
> headless auth + a machine user), the same ledger also drives the human-run L0/L1 `/ship-issue` order.

> **Owner:** AI generates, human reviews by sampling. This is derivation, not design — the
> judgment was spent at the freeze. If you find yourself *inventing* scope here, stop: that is
> a design gap and it goes back upstream through `/change-scope`, not forward into an issue.

## Preconditions — verify all
- The design is frozen: `POLICY.md` + `CONTEXT.md` exist and the `design-freeze/v1` tag is set.
- Frozen-track artifacts present: `docs/roadmap.md`, `docs/PRD.md`, `docs/api-spec.yaml`,
  `docs/erd.dbml`, `docs/api-frontend-reference.yaml`, and (webapp) `docs/views.md`, plus any
  `docs/research/msd_*.md`.
- Zero live `[NEEDS CLARIFICATION]` markers in frozen-track files. If any remain, stop — the
  design is not actually frozen.

## What you do

### 1. Slice the roadmap into issues
For each phase in `docs/roadmap.md` (MVP → V1 → V2), decompose the phase's stories into the
smallest **self-contained, independently shippable** units. One issue = one PR's worth of work.
Each issue must be derivable entirely from the frozen specs — cite the spec section it
implements (endpoint in `api-spec.yaml`, table in `erd.dbml`, action row in
`api-frontend-reference.yaml`, model in `msd_*.md`).

### 2. Write each issue self-contained
Every issue carries everything a fresh builder process needs, because it will be built with no
memory of any other issue:
- **Context** — what this is and which spec section governs it.
- **Exact task** — no more, no less.
- **Files** — the paths it may touch (and only those).
- **`verification:` block** — executable commands whose **exit codes define done**. A criterion
  you cannot express as a command or test is incomplete design → back upstream, not forward.
- **Labels** — `phase:<mvp|v1|v2>`, `type:<feat|fix|chore|infra>`, `model:<haiku|sonnet|opus>`,
  `complexity:<low|medium|high>`.
- **Dependencies** — the issue ids this one needs `merged` first.

### 3. DAG sanity
The dependency graph must be **acyclic** and **phase-consistent** (an MVP issue never depends on
a V1 issue). Every PRD story must map to ≥1 issue (preflight Step 15 re-checks this both ways).
Assign each issue a `start_date`/`end_date` inside its phase's roadmap window.

### 4. Emit `docs/GITHUB_ISSUES.md`
One section per issue, in execution (dependency) order. `/bootstrap-github` parses this file, so
keep the shape exact:

```markdown
## T001I1: <title>
**Phase:** mvp   **Type:** feat   **Model:** sonnet   **Complexity:** medium
**Depends on:** none
**Start date:** 2026-07-20   **End date:** 2026-07-21
**Spec:** api-spec.yaml `POST /links`; erd.dbml `links`

### Context
<why this exists; the frozen section it implements>

### Task
<the exact, bounded work>

### Files
- backend/app/routers/links.py
- backend/tests/test_links.py

### verification:
```bash
pytest backend/tests/test_links.py -q
schemathesis run docs/api-spec.yaml --base-url http://localhost:8000 --endpoint /links
```
```

### 5. Emit `.vector/issues.json` — the machine ledger
The runner reads this, not the Markdown. Same content, machine shape. Every issue starts
`"status": "queued"`. Ids are `T<NNN>I<N>` (matching the merge tag `vector/T<NNN>I<N>`).

```json
{
  "method_version": "2.0.0",
  "profile": "webapp",
  "generated_at": "{{ISO_DATE}}",
  "phases": ["mvp", "v1", "v2"],
  "issues": [
    {
      "id": "T001I1",
      "title": "Create link endpoint",
      "phase": "mvp",
      "type": "feat",
      "model": "sonnet",
      "complexity": "medium",
      "deps": [],
      "files": ["backend/app/routers/links.py", "backend/tests/test_links.py"],
      "verification": ["pytest backend/tests/test_links.py -q"],
      "spec_refs": ["api-spec.yaml#POST /links", "erd.dbml#links"],
      "start_date": "2026-07-20",
      "end_date": "2026-07-21",
      "status": "queued"
    }
  ]
}
```

### 6. Self-check before handing off
- `.vector/issues.json` parses; every `deps` id exists; the graph is acyclic (no cycle).
- Every issue has a non-empty `verification` block.
- The Markdown and the JSON list the **same** issue ids (count and set match).
- Every PRD story is covered by ≥1 issue.

```bash
python3 -c "import json,sys; d=json.load(open('.vector/issues.json')); iss=d['issues']; ids={i['id'] for i in iss}; \
assert all(all(x in ids for x in i['deps']) for i in iss), 'dangling dep'; \
assert all(i['verification'] for i in iss), 'issue with empty verification'; \
g={i['id']:set(i['deps']) for i in iss}; done=set(); \
[done.update(k for k,dep in g.items() if k not in done and dep<=done) for _ in ids]; \
assert done==ids, 'CYCLE in the dependency DAG: '+str(ids-done); print(len(ids),'issues, ledger consistent + acyclic')"
```

### 7. Hand to the human for a sampling review
Present a summary (issues per phase, the DAG, any issue whose verification felt thin). The human
spot-checks; they do not review every issue (that is what the freeze bought). Then: `/handover`.

## Hard rules
- Every acceptance criterion is an executable command. "Looks right" is not a criterion.
- Never invent scope to fill a gap. A gap is a design defect → `/change-scope`, not a new issue.
- The Markdown is the human mirror; `.vector/issues.json` is the source of truth for the runner.
  Keep them identical.
- Profile note: for `service-api`, there are no view/mock issues; Step-5 rows are consumer↔endpoint
  contracts. Everything else is identical.
