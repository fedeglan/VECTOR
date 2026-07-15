# VECTOR command-breadth sweep — latent first-run bugs (2026-07-15)

> After the pilot proved that unexercised commands carry real first-run bugs (it caught 2), a
> multi-agent sweep hunted the same classes across all 28 commands: broken paths, wrong CLI
> syntax/flag-typing, shell gotchas, unshipped-uncaveated references, missing producers, profile
> gaps. Each finding was adversarially verified. **27 confirmed; 9 commands came back clean**
> (audit-plan, clarify, escalate, explain-pr, explore, test-plan, triage, + two more).

## Fixed in this pass (branch `v2-command-hardening`)

| Sev | Command | Bug | Fix |
|---|---|---|---|
| **high** | change-scope + `frozen_specs.py` | The command claims the hooks make an exception for editing frozen specs, but the hook implemented **none** — so the only sanctioned mutation path is itself blocked. `/change-scope` is non-functional in a hooked project. | Implemented a narrow marker window: `frozen_specs.py` honors `.vector/change-scope-open`; `/change-scope` opens it, edits, closes it. CODEOWNERS still gates the merge. Battery case added (open→allowed, shut→blocked). |
| **high** | bootstrap-github | Step 7 asserts `ledger == gh issue list … --jq length`, but `gh issue list` defaults to `--limit 30` — so **any project with >30 issues aborts** even when correct. | Added `--limit 10000` to both `gh issue list` calls. |
| **high** | ship-issue | The rollback tag `vector/T<NNN>I<N>` is created locally but **never pushed** — an unpushed tag is not a rollback handle. (Hit live in the pilot.) | Added `git push origin vector/T<NNN>I<N>`. |
| **high** | handover | The coverage baseline is initialized by running `pytest --cov` before any tests exist → no `coverage.xml` → baseline never written → the first `coverage-ratchet` CI job fails as "missing baseline". (Hit live in the pilot.) | Robust init: set from a real `coverage.xml` if present, else seed a committed `0.0` floor; documented that it must be raised deliberately or stays toothless. |
| **high** | upgrade-project (×3) | Installs the CI **workflows** but not their **producers**: the `.github/scripts` CI helpers the workflows invoke, the `.claude/hooks/tests` battery preflight re-runs, and the coverage baseline — so every PR red-checks. | Rewrote Step 3 with concrete copy blocks for the hooks+tests, CI scripts, workflow templates, baseline init, and CODEOWNERS-with-substitution. |
| **medium** | bootstrap-github | Step 3 discards `gh project create` output (no project number captured) and Step 4 writes Start/End dates to **fields that don't exist** on a fresh Projects v2 board. | Capture `$PROJ`; create the Start/End DATE fields; note the `project` token scope. |
| **medium** | upgrade-project | CODEOWNERS installed with its `{{HUMAN_GITHUB_USER}}` placeholder unreplaced → silently voids frozen-path protection. | Substitution + placeholder self-check added (folded into the Step 3 rewrite). |
| **medium** | setup | Step 8's mandatory hook-battery block uses an undefined `<plugin>` placeholder. | Resolve via `PLUGIN="${CLAUDE_PLUGIN_ROOT:-.}"`. |
| **medium** | handover | Self-check validated the workflow-level `name:`, not the job/check-run context branch protection actually requires. | Parse each job's `name`/key (the real check-run context). |
| **medium** | mock | The Step-9 mock gate is never persisted (`mock/` is gitignored), so `/resume` cannot detect it. | Persist a dated `## Mock gate — passed <date>` line into `docs/views.md`. |
| **medium** | freeze-design | *(from the pilot preflight run)* The freeze checklist doesn't assert the frozen **YAML actually parses**; an unquoted `{id}` in an inline flow-mapping silently makes `api-frontend-reference.yaml` invalid YAML. | Added a `yaml.safe_load` assertion to the freeze checklist. |

## Deferred — documented, not fixed this pass

- **medium — bootstrap-github Step 7 protection read is admin-only** while Step 0 prescribes a
  *write-only* least-privilege machine user, so a least-privilege bot 403s at verification. Needs a
  design reconciliation (admin required to bootstrap/verify protection vs least-privilege for
  steady-state), so it is raised rather than silently patched.
- **low (×13)** — mostly unshipped-runner caveats missing on a few `resume.md`/`run-phase.md` lines,
  a `report-bug.md` service-api profile note, a deprecated `docker-compose` (vs `docker compose`)
  spelling, a `generate-issues` self-check that says "acyclic" without checking cycles, and the
  `baselines/` producer-path being unstated. None blocks a first run; batched for a later polish.

## Net effect on confidence

This directly attacks the reason the post-pilot rating sat at **7 and not 8**: the ~25 unexercised
commands. The sweep found the same *class* of first-run bug the pilot did (paths, CLI typing) across
several commands — the most serious being `/change-scope` being unable to mutate. With the high/medium
fixes landed and the batteries green (`make test`: 37/37 + 10/10 + 26/26 + 18/18 + 8/8), the breadth
risk is materially reduced. It still isn't zero — most commands were audited statically, not executed
end-to-end like 12→13→14 were — so the honest rating for the scoped 2.0.0 moves to **~7.5**, held
short of 8 only by "static-audited, not run" and the single-identity/webapp-visual gaps.
