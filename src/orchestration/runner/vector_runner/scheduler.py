"""Scheduling — ready set, park-and-continue, breakers, freeze-class (SPEC §2.2/§2.4).

Semantics are byte-identical to tests/fsm_sim.py:
- ready(): sorted iteration; a queued issue whose deps include an escalated (or
  transitively blocked) issue is parked as blocked-by-escalation; a queued issue is
  ready when ALL deps are merged. Park-and-continue falls out of this scan.
- Breaker: only budget-class terminal failures increment consecutive_failures
  (once per issue). Ambiguity, review-deadlock and spec-conflict do NOT — design
  signals, not build instability. Rate-limit infra-pauses NEVER touch the counter.
- Freeze-class: a spec-conflict transitively blocking >50% of the REMAINING dag
  halts the phase.
"""
from . import state as state_mod


def ready(st):
    """Next ready issue id, or None. Mutates parked statuses exactly like the sim."""
    iss = st.issues
    for iid in sorted(iss):
        it = iss[iid]
        if it["status"] != "queued":
            continue
        deps = it.get("deps", [])
        if any(iss[d]["status"] in ("escalated", "blocked-by-escalation") for d in deps):
            st.set_status(iid, "blocked-by-escalation")
            continue
        if all(iss[d]["status"] == "merged" for d in deps):
            return iid
    return None


def transitively_blocked_by(st, item, root):
    seen, stack = set(), list(item.get("deps", []))
    while stack:
        d = stack.pop()
        if d == root:
            return True
        if d in seen:
            continue
        seen.add(d)
        stack.extend(st.issues[d].get("deps", []))
    return False


def escalate(st, policy, iid, reason, count_failure, question="", positions=""):
    """Terminal escalation for an issue. Feeds breaker only for budget-class."""
    st.set_status(iid, "escalated")
    it = st.issues[iid]
    it["esc_reason"] = reason
    it["esc_ts"] = state_mod.now_iso()
    if question:
        it["esc_question"] = question
    if positions:
        it["esc_positions"] = positions
    if count_failure:
        st.st["consecutive_failures"] += 1
        if st.st["consecutive_failures"] >= policy["breakers"]["consecutive_terminal_failures"]:
            st.st["halted"] = "breaker:consecutive-failures"
    # freeze-class: spec conflict blocking >50% of the REMAINING dag
    if reason == "spec-conflict":
        remaining = [i for i in st.issues.values()
                     if i["status"] in ("queued", "blocked-by-escalation")]
        blocked = [i for i in remaining if transitively_blocked_by(st, i, iid)]
        if remaining and len(blocked) / len(remaining) > 0.5:
            st.st["halted"] = "freeze:spec-conflict"
    st.persist()


def merged(st, iid):
    """A clean merge resets the consecutive-failure counter (SPEC §2.4)."""
    st.set_status(iid, "merged")
    st.st["consecutive_failures"] = 0
    st.persist()


def requeue_spec_conflicts(st, change_scope_ts_fn):
    """Return path (SPEC §2.4): spec-conflict issues re-queue ONLY if a /change-scope
    record newer than the escalation exists. change_scope_ts_fn() -> newest record ts
    (ISO string) or None."""
    newest = change_scope_ts_fn()
    if not newest:
        return []
    requeued = []
    for iid in sorted(st.issues):
        it = st.issues[iid]
        if it["status"] == "escalated" and it.get("esc_reason") == "spec-conflict" \
                and it.get("esc_ts") and newest > it["esc_ts"]:
            it["status"] = "queued"
            it.pop("esc_reason", None)
            st.st["log"].append(f"{iid}:requeued-after-change-scope")
            requeued.append(iid)
            # unblock dependents parked on this escalation
            for jid in sorted(st.issues):
                jt = st.issues[jid]
                if jt["status"] == "blocked-by-escalation":
                    jt["status"] = "queued"
                    st.st["log"].append(f"{jid}:unparked")
    if requeued:
        st.persist()
    return requeued


def requeue_in_flight(st):
    """Resume semantics: an issue killed mid-pipeline (building/pr-open/ci-pending/
    in-review/changes-requested) returns to queued with its budget counters PRESERVED —
    a killed attempt still consumed budget. Terminal statuses are untouched, which is
    what makes S5 (resume == uninterrupted) hold."""
    requeued = []
    for iid in sorted(st.issues):
        s = st.issues[iid]["status"]
        if s.startswith("building(") or s in ("pr-open", "ci-pending", "in-review",
                                              "changes-requested"):
            st.issues[iid]["status"] = "queued"
            st.st["log"].append(f"{iid}:requeued-on-resume")
            requeued.append(iid)
    if requeued:
        st.persist()
    return requeued
