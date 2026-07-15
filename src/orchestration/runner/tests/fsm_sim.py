#!/usr/bin/env python3
"""VECTOR relay-runner FSM simulator — the ORCHESTRATION SPEC executed as a program.
Mocked agents (scripted outcomes), real state machine, real persistence (state.json
after EVERY transition), real breakers/budgets/park-and-continue. Seven scenarios.

This is the executable specification of the runner's control flow (Phase B builds the
real runner against it). Validated pre-freeze: 8/8. Run: python3 fsm_sim.py"""
import json, os, tempfile, copy

POLICY = {"build_attempts": 3, "review_cycles": 2, "consecutive_failures_halt": 3}

# ---------------- mocked agents ----------------
class MockAgents:
    """Scripted per-issue outcomes. build: list of 'ok'|'failed'|'blocked'.
    ci: list of 'green'|'red'. review: list of 'APPROVED'|'CHANGES_REQUESTED'."""
    def __init__(self, script): self.s = copy.deepcopy(script)
    def _pop(self, iid, kind, default):
        q = self.s.get(iid, {}).get(kind, [])
        return q.pop(0) if q else default
    def build(self, iid):  return self._pop(iid, "build", "ok")
    def ci(self, iid):     return self._pop(iid, "ci", "green")
    def review(self, iid): return self._pop(iid, "review", "APPROVED")

# ---------------- runner ----------------
class Runner:
    def __init__(self, statefile, issues=None, agents=None, level="L2", policy=POLICY):
        self.f, self.agents, self.policy = statefile, agents, policy
        if issues is not None:
            self.st = {"level": level, "consecutive_failures": 0, "halted": None,
                       "shadow": [], "log": [],
                       "issues": {i["id"]: {**i, "status": "queued", "attempts": 0, "rejections": 0}
                                  for i in issues}}
            self._persist()
        else:
            with open(statefile) as fh: self.st = json.load(fh)  # resume path

    def _persist(self):
        with open(self.f, "w") as fh: json.dump(self.st, fh)

    def _set(self, iid, status):
        self.st["issues"][iid]["status"] = status
        self.st["log"].append(f"{iid}:{status}")
        self._persist()                                   # after EVERY transition

    def _ready(self):
        iss = self.st["issues"]
        for iid in sorted(iss):
            it = iss[iid]
            if it["status"] != "queued": continue
            deps = it.get("deps", [])
            if any(iss[d]["status"] == "escalated" or iss[d]["status"] == "blocked-by-escalation" for d in deps):
                self._set(iid, "blocked-by-escalation"); continue
            if all(iss[d]["status"] == "merged" for d in deps):
                return iid
        return None

    def _escalate(self, iid, reason, count_failure):
        self._set(iid, "escalated")
        self.st["issues"][iid]["esc_reason"] = reason
        if count_failure:
            self.st["consecutive_failures"] += 1
            if self.st["consecutive_failures"] >= self.policy["consecutive_failures_halt"]:
                self.st["halted"] = "breaker:consecutive-failures"
        else:
            pass  # ambiguity escalations do not feed the failure breaker
        # freeze-class: spec conflict blocking >50% of REMAINING dag
        if reason == "spec-conflict":
            remaining = [i for i in self.st["issues"].values() if i["status"] in ("queued", "blocked-by-escalation")]
            blocked = [i for i in remaining if self._transitively_blocked_by(i, iid)]
            if remaining and len(blocked) / len(remaining) > 0.5:
                self.st["halted"] = "freeze:spec-conflict"
        self._persist()

    def _transitively_blocked_by(self, item, root):
        seen, stack = set(), list(item.get("deps", []))
        while stack:
            d = stack.pop()
            if d == root: return True
            if d in seen: continue
            seen.add(d); stack.extend(self.st["issues"][d].get("deps", []))
        return False

    def _pipeline(self, iid):
        """build -> ci -> review -> (fix cycles) -> merge. One fresh 'process' per role."""
        it = self.st["issues"][iid]
        while True:
            # BUILD (attempt k)
            it["attempts"] += 1; self._set(iid, f"building({it['attempts']})")
            out = self.agents.build(iid)
            if out == "blocked":                           # spec ambiguity: escalate IMMEDIATELY, no retries
                return self._escalate(iid, "ambiguity", count_failure=False)
            if out == "failed":
                if it["attempts"] >= self.policy["build_attempts"]:
                    return self._escalate(iid, "budget:build-attempts", count_failure=True)
                continue
            if out == "spec-conflict":
                return self._escalate(iid, "spec-conflict", count_failure=False)
            self._set(iid, "pr-open")
            # CI
            self._set(iid, "ci-pending")
            if self.agents.ci(iid) == "red":
                if it["attempts"] >= self.policy["build_attempts"]:
                    return self._escalate(iid, "budget:build-attempts", count_failure=True)
                continue                                   # ci-red -> building(k+1)
            # REVIEW (fresh context)
            self._set(iid, "in-review")
            verdict = self.agents.review(iid)
            if self.st["level"] == "L1":
                human = self.agents._pop(iid, "human", "APPROVED")   # shadow: human is the merger
                self.st["shadow"].append({"issue": iid, "reviewer": verdict, "human": human,
                                          "diverged": verdict != human})
                if human == "APPROVED":
                    self._set(iid, "merged"); self.st["consecutive_failures"] = 0; self._persist(); return
                verdict = "CHANGES_REQUESTED"              # human asked for changes -> fix cycle
            if verdict == "APPROVED":
                self._set(iid, "merged"); self.st["consecutive_failures"] = 0; self._persist(); return
            it["rejections"] += 1
            if it["rejections"] > self.policy["review_cycles"]:      # third rejection = escalate
                return self._escalate(iid, "review-deadlock", count_failure=False)
            self._set(iid, "changes-requested")            # -> building(k+1)

    def run(self, max_steps=100):
        steps = 0
        while not self.st["halted"] and steps < max_steps:
            iid = self._ready()
            if iid is None: break
            self._pipeline(iid); steps += 1
        self._persist()
        return self.st

# ---------------- scenarios ----------------
def S(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL':4} | {name}" + (f" | {detail}" if detail and not cond else ""))
    return cond

def statuses(st): return {k: v["status"] for k, v in st["issues"].items()}

def main():
    ok = True
    tmp = tempfile.mkdtemp()

    # S1 happy path, DAG respected (A -> B; C independent), L2 autonomous merges
    f = os.path.join(tmp, "s1.json")
    r = Runner(f, [{"id":"A"},{"id":"B","deps":["A"]},{"id":"C"}], MockAgents({}), level="L2")
    st = r.run()
    log = [l for l in st["log"] if l.endswith(":merged")]
    ok &= S("S1 happy path: all merged, deps respected",
            statuses(st) == {"A":"merged","B":"merged","C":"merged"} and log.index("A:merged") < log.index("B:merged"))

    # S2 build fails 3x on B -> escalated; D (dep B) blocked; C independent still merges (park-and-continue)
    f = os.path.join(tmp, "s2.json")
    r = Runner(f, [{"id":"A"},{"id":"B","deps":["A"]},{"id":"C"},{"id":"D","deps":["B"]}],
               MockAgents({"B": {"build": ["failed","failed","failed"]}}), level="L2")
    st = r.run()
    ok &= S("S2 park-and-continue: B escalated, D blocked, C merged",
            statuses(st)["B"] == "escalated" and statuses(st)["D"] == "blocked-by-escalation"
            and statuses(st)["C"] == "merged" and st["halted"] is None)

    # S2b 'blocked' (ambiguity) escalates IMMEDIATELY, single attempt, no failure-breaker feed
    f = os.path.join(tmp, "s2b.json")
    r = Runner(f, [{"id":"A"}], MockAgents({"A": {"build": ["blocked"]}}), level="L2")
    st = r.run()
    ok &= S("S2b ambiguity: immediate escalation, 1 attempt, breaker untouched",
            statuses(st)["A"] == "escalated" and st["issues"]["A"]["attempts"] == 1
            and st["consecutive_failures"] == 0)

    # S3 reviewer rejects 3x -> review-deadlock escalation after 2 fix cycles
    f = os.path.join(tmp, "s3.json")
    r = Runner(f, [{"id":"A"}], MockAgents({"A": {"review": ["CHANGES_REQUESTED"]*3}}), level="L2")
    st = r.run()
    ok &= S("S3 review deadlock: escalated on 3rd rejection",
            statuses(st)["A"] == "escalated" and st["issues"]["A"]["esc_reason"] == "review-deadlock"
            and st["issues"]["A"]["rejections"] == 3)

    # S4 breaker: 3 consecutive issue failures -> run halted, remaining stays queued
    f = os.path.join(tmp, "s4.json")
    fail3 = {"build": ["failed"]*3}
    r = Runner(f, [{"id":"A"},{"id":"B"},{"id":"C"},{"id":"D"}],
               MockAgents({"A": fail3, "B": copy.deepcopy(fail3), "C": copy.deepcopy(fail3)}), level="L2")
    st = r.run()
    ok &= S("S4 breaker: halt after 3 consecutive failures, D untouched",
            st["halted"] == "breaker:consecutive-failures" and statuses(st)["D"] == "queued")

    # S5 kill/resume: interrupt after A merges; resumed run must equal uninterrupted run
    f5a, f5b = os.path.join(tmp, "s5a.json"), os.path.join(tmp, "s5b.json")
    issues5 = [{"id":"A"},{"id":"B","deps":["A"]},{"id":"C","deps":["B"]}]
    ref = Runner(f5a, copy.deepcopy(issues5), MockAgents({}), level="L2").run()      # uninterrupted
    r = Runner(f5b, copy.deepcopy(issues5), MockAgents({}), level="L2")
    r._pipeline("A")                                       # ... then process dies
    r2 = Runner(f5b, agents=MockAgents({}))                # resume purely from state.json
    st = r2.run()
    ok &= S("S5 kill/resume: state-file resume == uninterrupted run",
            statuses(st) == statuses(ref) and st["level"] == "L2")

    # S6 L1 shadow: reviewer diverges, human merges anyway; divergence recorded; level never raised
    f = os.path.join(tmp, "s6.json")
    r = Runner(f, [{"id":"A"},{"id":"B"}],
               MockAgents({"A": {"review": ["CHANGES_REQUESTED"], "human": ["APPROVED"]}}), level="L1")
    st = r.run()
    div = [s for s in st["shadow"] if s["diverged"]]
    ok &= S("S6 shadow mode: human merged, divergence 1/2 recorded, level still L1",
            statuses(st) == {"A":"merged","B":"merged"} and len(st["shadow"]) == 2
            and len(div) == 1 and st["level"] == "L1")

    # S7 freeze-class: spec conflict on A blocking >50% of remaining DAG -> phase freeze
    f = os.path.join(tmp, "s7.json")
    r = Runner(f, [{"id":"A"},{"id":"B","deps":["A"]},{"id":"C","deps":["A"]},{"id":"D"}],
               MockAgents({"A": {"build": ["spec-conflict"]}}), level="L2")
    st = r.run()
    ok &= S("S7 freeze-class: spec-conflict blocking >50% remaining -> halted",
            st["halted"] == "freeze:spec-conflict" and statuses(st)["A"] == "escalated")

    print("\nALL SCENARIOS " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
