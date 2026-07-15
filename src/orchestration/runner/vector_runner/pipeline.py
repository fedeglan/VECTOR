"""The per-issue pipeline and the run loop (SPEC §2.3) — control flow byte-identical
to tests/fsm_sim.py, with the real-world steps (spawn, CI, gh) in between.

build -> ci -> review -> (fix cycles) -> merge. One fresh process per role.
- blocked (ambiguity): escalate IMMEDIATELY, single attempt, breaker untouched.
- failed build / CI-red: same build_attempts budget (no hidden retry pocket);
  exhaustion escalates budget-class (feeds the breaker).
- CI infra failure: retry once, then escalate infra (environment, not build
  instability — does not feed the breaker).
- rate-limit under subscription: INFRA-PAUSE — park, do not consume the attempt,
  never a failure, never a breaker event (SPEC §2.2).
- review: fresh context; 3rd rejection -> review-deadlock (no breaker feed).
- L1 shadow: verdict recorded to shadow.json; the HUMAN merges; divergence logged.
- merge: gh merge + annotated tag pushed + SESSIONS.md entry + counter reset.
"""
import json
import os
import time

from . import gates, scheduler, spawn
from .policy import reviewer_model
from .state import now_iso


class Hooks:
    """Side-effect seams the CLI wires up; kept injectable so the control flow is
    testable with the REAL runner code (never a mocked state machine)."""
    def __init__(self, cwd, policy, sessions_path="SESSIONS.md",
                 escalations_path="ESCALATIONS.md", shadow_path=".vector/shadow.json",
                 sleep=time.sleep):
        self.cwd = cwd
        self.policy = policy
        self.sessions_path = os.path.join(cwd, sessions_path)
        self.escalations_path = os.path.join(cwd, escalations_path)
        self.shadow_path = os.path.join(cwd, shadow_path)
        self.sleep = sleep

    def log_session(self, line):
        with open(self.sessions_path, "a") as fh:
            fh.write(line.rstrip() + "\n")

    def log_escalation(self, st, iid, reason, question, context=""):
        """The full six-field escalate.md template (R-ESC-04) — header carries no
        (needs-human) suffix (that is a GitHub label, not part of the entry). The
        dependents/continuing sets are computed from state at escalation time."""
        dependents = _dependents(st, iid)
        continuing = _continuing(st, iid)
        dep = ", ".join(dependents) if dependents else "none"
        cont = ", ".join(continuing) if continuing else "none"
        with open(self.escalations_path, "a") as fh:
            fh.write(
                f"\n## {now_iso()} — {iid} — {reason}\n"
                f"**Decision needed:** {question or '(see state.json)'}\n"
                f"**Context:** {context or 'see .vector/state.json for the attempt trail'}\n"
                f"**Options considered:** (none pre-selected — the human decides)\n"
                f"**Blocked:** {iid} · **Also blocked (dependents):** {dep}\n"
                f"**Independent work continuing:** {cont}\n")

    def record_shadow(self, entry):
        data = []
        if os.path.exists(self.shadow_path):
            with open(self.shadow_path) as fh:
                data = json.load(fh)
        data.append(entry)
        os.makedirs(os.path.dirname(self.shadow_path), exist_ok=True)
        with open(self.shadow_path, "w") as fh:
            json.dump(data, fh, indent=1)


def _issue_model(it):
    return it.get("model", "sonnet")


def _run_hours_exceeded(st, policy):
    return (time.time() - st.st.get("run_started_at", time.time())) / 3600.0 \
        >= policy["budgets"]["hours_per_run"]


def _remaining_secs(it, budgets):
    """R-BUD-04: the whole issue (build + CI wait + review) is bounded by
    minutes_per_issue. Every spawn/poll gets the REMAINDER, and every spawn charges its
    wall time to it['wall_secs']."""
    return max(1, budgets["minutes_per_issue"] * 60 - it.get("wall_secs", 0))


def _dependents(st, iid):
    return [j for j in sorted(st.issues)
            if scheduler.transitively_blocked_by(st, st.issues[j], iid)
            and st.issues[j]["status"] in ("queued", "blocked-by-escalation")]


def _continuing(st, iid):
    return [j for j in sorted(st.issues)
            if st.issues[j]["status"] == "queued" and j != iid
            and not scheduler.transitively_blocked_by(st, st.issues[j], iid)]


def _complete_merge(st, policy, hooks, iid):
    """Crash-safe merge (findings R-STA-01/R-MRG-01/R-MRG-04): a durable 'merging'
    marker is written BEFORE the platform merge; the merged status is persisted
    IMMEDIATELY after the merge succeeds, BEFORE the tag push; a merge GateError routes
    to an infra escalation (park-and-continue, never a crash); a tag-push failure keeps
    the completed merge and never unwinds it. Idempotent under resume."""
    it = st.issues[iid]
    cwd = hooks.cwd
    pr = it["pr"]
    st.set_status(iid, "merging")                       # write-ahead marker
    try:
        gates.do_merge(pr, cwd, policy["merge"]["target"])
    except gates.GateError as e:
        # not a code fault and not 'already merged' -> environment/transient: escalate
        # infra so independent branches keep running (never crash the loop).
        scheduler.escalate(st, policy, iid, "infra", count_failure=False,
                           question=f"merge failed for PR {pr}: {e}")
        hooks.log_escalation(st, iid, "infra", f"merge failed for PR {pr}: {e}",
                             context=str(e))
        return "escalated"
    scheduler.merged(st, iid)                            # persist merged BEFORE the tag
    gates.close_issue(it.get("gh"), pr, cwd)
    try:
        it["tag"] = gates.tag_merge(iid, pr, cwd)
        st.persist()
    except gates.GateError as e:
        # the merge is DONE and recorded; a tag-push failure is a rollback-handle gap,
        # not a reason to un-merge or crash. Flag it and continue.
        st.event("tag-push-failed", f"{iid}: {e}")
    hooks.log_session(_session_line(st, iid))
    return "merged"


def run_issue(st, policy, hooks, iid):
    """Drive one issue to a terminal status. Returns the terminal status string."""
    it = st.issues[iid]
    cwd = hooks.cwd
    budgets = policy["budgets"]
    level = st.level
    failure_log, blockers = None, None

    while True:
        # ---- BUILD (attempt k) -------------------------------------------------
        # minutes_per_issue is a PER-ISSUE wall budget: each spawn gets the remainder
        remaining = budgets["minutes_per_issue"] * 60 - it.get("wall_secs", 0)
        if remaining <= 0:
            scheduler.escalate(st, policy, iid, "budget:minutes-per-issue",
                               count_failure=True,
                               question="per-issue wall-time budget exhausted")
            hooks.log_escalation(st, iid, "budget", "minutes_per_issue exhausted")
            return "escalated"
        it["attempts"] += 1
        st.set_status(iid, f"building({it['attempts']})")
        res = spawn.build(iid, _issue_model(it), cwd, policy, level,
                          it["attempts"], failure_log=failure_log, blockers=blockers,
                          timeout_secs=remaining)
        failure_log, blockers = None, None
        it["tokens"] = it.get("tokens", 0) + res.tokens
        it["wall_secs"] = it.get("wall_secs", 0) + int(res.wall_secs)
        st.persist()

        if res.outcome == "rate-limited":
            # infra-pause: the attempt consumed nothing — give it back, park, retry.
            # hours_per_run still bounds the PARKED run (a permanent window must not
            # loop forever): halt cleanly; resume re-queues the in-flight issue.
            it["attempts"] -= 1
            st.event("infra-pause", f"{iid}: rate-limit window; parked")
            if _run_hours_exceeded(st, policy):
                st.halt("budget:hours-per-run")
                return "halted"
            hooks.sleep(int(os.environ.get("VECTOR_RATELIMIT_PARK_SECS", "300")))
            continue
        if res.outcome == "blocked":
            q = res.data.get("question", "")
            scheduler.escalate(st, policy, iid, "ambiguity", count_failure=False,
                               question=q)
            hooks.log_escalation(st, iid, "ambiguity", q)
            gates.escalation_labels(it.get("gh"), cwd, q)
            return "escalated"
        if res.outcome == "spec-conflict":
            p = res.data.get("positions", "") or res.data.get("question", "")
            scheduler.escalate(st, policy, iid, "spec-conflict", count_failure=False,
                               positions=p)
            hooks.log_escalation(st, iid, "spec-conflict", p)
            gates.escalation_labels(it.get("gh"), cwd, p)
            return "escalated"
        if res.outcome == "failed":
            if it["attempts"] >= budgets["build_attempts"]:
                scheduler.escalate(st, policy, iid, "budget:build-attempts",
                                   count_failure=True,
                                   question=res.data.get("reason", "build attempts exhausted"))
                hooks.log_escalation(st, iid, "budget", res.data.get("reason", ""))
                return "escalated"
            failure_log = json.dumps(res.data)
            continue

        # pr-open
        pr = res.data.get("pr") or it.get("pr")
        if not pr:
            # a "pr-open" outcome without a PR number is a failed attempt, honestly
            if it["attempts"] >= budgets["build_attempts"]:
                scheduler.escalate(st, policy, iid, "budget:build-attempts",
                                   count_failure=True, question="builder reported pr-open without a PR number")
                hooks.log_escalation(st, iid, "budget", "pr-open without PR number")
                return "escalated"
            failure_log = "builder reported pr-open but no PR number was found"
            continue
        it["pr"] = pr
        it["branch"] = res.data.get("branch") or it.get("branch")
        # R-SPN-08: the PR must genuinely belong to THIS issue before we trust it
        ok, why = gates.verify_pr(pr, iid, cwd, policy["merge"]["target"],
                                  policy["merge"].get("bot_identity"))
        if not ok:
            if it["attempts"] >= budgets["build_attempts"]:
                scheduler.escalate(st, policy, iid, "budget:build-attempts",
                                   count_failure=True, question=why)
                hooks.log_escalation(st, iid, "budget", why, context=why)
                return "escalated"
            failure_log = f"builder-reported PR rejected: {why}"
            continue
        st.set_status(iid, "pr-open")

        # ---- CI ----------------------------------------------------------------
        st.set_status(iid, "ci-pending")
        infra_retries = 0
        while True:
            ci_state, names, tail = gates.wait_ci(
                pr, cwd, policy["merge"]["required_checks"],
                timeout_secs=_remaining_secs(it, budgets))
            if ci_state == "infra-red":
                if infra_retries < 1:
                    infra_retries += 1
                    st.event("ci-infra-retry", f"{iid}: {names}")
                    continue
                scheduler.escalate(st, policy, iid, "infra", count_failure=False,
                                   question=f"CI infra failure persisted: {names}")
                hooks.log_escalation(st, iid, "infra", f"CI infra failure: {names}")
                return "escalated"
            break
        if ci_state == "red":
            if it["attempts"] >= budgets["build_attempts"]:
                scheduler.escalate(st, policy, iid, "budget:build-attempts",
                                   count_failure=True,
                                   question=f"CI red on final attempt: {names}")
                hooks.log_escalation(st, iid, "budget", f"CI red: {names}")
                return "escalated"
            failure_log = gates.failure_log(pr, cwd) or f"CI red: {names}"
            continue  # ci-red -> building(k+1); same budget

        # ---- REVIEW (fresh context) -------------------------------------------
        st.set_status(iid, "in-review")
        rmodel = reviewer_model(_issue_model(it),
                                complexity_high=(it.get("complexity") == "high"))
        fail_retries = 0
        while True:
            rres = spawn.review(pr, rmodel, cwd, policy,
                                timeout_secs=_remaining_secs(it, budgets))
            it["tokens"] = it.get("tokens", 0) + rres.tokens
            it["wall_secs"] = it.get("wall_secs", 0) + int(rres.wall_secs)
            st.persist()
            if rres.outcome == "rate-limited":
                # infra-pause, never a failure — park and re-spawn (SPEC §2.2)
                st.event("infra-pause", f"{iid}: reviewer rate-limited; parked")
                if _run_hours_exceeded(st, policy):
                    st.halt("budget:hours-per-run")
                    return "halted"
                hooks.sleep(int(os.environ.get("VECTOR_RATELIMIT_PARK_SECS", "300")))
                continue
            if rres.outcome == "failed":
                # reviewer infra: retry once then escalate infra (not build instability)
                if fail_retries < 1:
                    fail_retries += 1
                    continue
                scheduler.escalate(st, policy, iid, "infra", count_failure=False,
                                   question="reviewer process failed twice")
                hooks.log_escalation(st, iid, "infra", "reviewer failed twice")
                return "escalated"
            break
        verdict = rres.outcome
        summary = rres.data.get("summary", "")
        it["review_summary"] = summary

        if rres.data.get("spec_conflict"):
            scheduler.escalate(st, policy, iid, "spec-conflict", count_failure=False,
                               positions=summary or "reviewer: the spec is wrong, not the code")
            hooks.log_escalation(st, iid, "spec-conflict", summary)
            return "escalated"

        gates.set_reviewer_approval(pr, cwd, verdict == "APPROVED", summary)

        # ---- L0/L1: the HUMAN is the merger (runner never merges below L2) -----
        # Shadow is recorded at both L0 and L1 (ship-issue §6 pins L0/L1; harmless
        # telemetry at L0, graduation telemetry at L1).
        if st.level in ("L0", "L1"):
            human, detail = _await_human(pr, cwd, hooks)
            entry = {"issue": iid, "pr": pr, "reviewer": verdict,
                     "human": "APPROVED" if human == "merged" else "CHANGES_REQUESTED",
                     "diverged": (verdict == "APPROVED") != (human == "merged"),
                     "ts": now_iso()}
            st.st["shadow"].append(entry)
            hooks.record_shadow(entry)
            st.persist()
            if human == "merged":
                scheduler.merged(st, iid)
                hooks.log_session(_session_line(st, iid))
                return "merged"
            verdict = "CHANGES_REQUESTED"  # human asked for changes -> fix cycle

        # ---- VERDICT -----------------------------------------------------------
        if verdict == "APPROVED":
            return _complete_merge(st, policy, hooks, iid)

        it["rejections"] += 1
        if it["rejections"] > policy["budgets"]["review_cycles"]:  # 3rd rejection
            scheduler.escalate(st, policy, iid, "review-deadlock", count_failure=False,
                               positions=json.dumps(rres.data.get("blockers", []))[-1500:])
            hooks.log_escalation(st, iid, "review-deadlock",
                                 "both positions in state.json")
            return "escalated"
        st.set_status(iid, "changes-requested")
        blockers = rres.data.get("blockers", [])
        # -> building(k+1): fix process on the SAME branch


def _await_human(pr, cwd, hooks, poll_secs=30):
    """L1: poll the PR until the human merges or requests changes."""
    while True:
        status, detail = gates.pr_merged_by_human(pr, cwd)
        if status in ("merged", "changes"):
            return status, detail
        hooks.sleep(poll_secs)


def _session_line(st, iid):
    it = st.issues[iid]
    return (f"| {now_iso()} | {iid} | PR#{it.get('pr','-')} | {it.get('tag','-')} | "
            f"tokens={it.get('tokens',0)} | wall={it.get('wall_secs',0)}s | "
            f"{(it.get('review_summary') or '')[:160]} |")


def reconcile_merging(st, policy, hooks):
    """Resume safety (R-STA-01): an issue killed AFTER the write-ahead 'merging' marker
    but before completion is finished idempotently — do_merge sees the PR already
    MERGED and skips, then the tag/log/status complete. If the merge never landed, it
    retries cleanly. Runs before the main loop on every resume."""
    for iid in sorted(st.issues):
        if st.issues[iid]["status"] == "merging":
            st.event("reconcile-merging", iid)
            _complete_merge(st, policy, hooks, iid)


def run(st, policy, hooks, max_steps=1000):
    """The run loop: issue boundaries check HALT, hours_per_run, and the window."""
    reconcile_merging(st, policy, hooks)
    steps = 0
    merges_since_cadence = 0
    halt_file = os.path.join(hooks.cwd, ".vector", "HALT")
    while not st.halted and steps < max_steps:
        if os.path.exists(halt_file):
            st.halt("halt-file")
            break
        elapsed_h = (time.time() - st.st.get("run_started_at", time.time())) / 3600.0
        if elapsed_h >= policy["budgets"]["hours_per_run"]:
            st.halt("budget:hours-per-run")
            break
        iid = scheduler.ready(st)
        if iid is None:
            break
        terminal = run_issue(st, policy, hooks, iid)
        steps += 1
        if terminal == "merged":
            merges_since_cadence += 1
            if merges_since_cadence >= 10:                     # SPEC §2.3.7 cadence
                merges_since_cadence = 0
                st.event("cadence", "10 merges: /audit-plan + explorer smoke due")
    st.persist()
    return st.st
