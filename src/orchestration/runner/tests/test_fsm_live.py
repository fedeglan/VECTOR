#!/usr/bin/env python3
"""Phase-B battery: the fsm_sim scenarios EXECUTED AGAINST THE REAL RUNNER, plus the
live behaviors the sim does not model. The only substitution is the external binaries
(claude/gh/git -> deterministic shims via VECTOR_*_BIN); every line of runner control
flow is the real code. Run: python3 test_fsm_live.py"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER_DIR = os.path.dirname(HERE)
SHIMS = os.path.join(HERE, "shims")
sys.path.insert(0, RUNNER_DIR)

from vector_runner import cli, pipeline, policy as policy_mod  # noqa: E402
from vector_runner.state import State  # noqa: E402

PASS = FAIL = 0


def S(name, cond, detail=""):
    global PASS, FAIL
    PASS += cond
    FAIL += (not cond)
    print(f"{'PASS' if cond else 'FAIL':4} | {name}" + (f" | {detail}" if detail and not cond else ""))
    return cond


POLICY_TMPL = """```yaml
method_version: 2.0.0
```
## 1. Autonomy level
```yaml
autonomy_level: {level}
```
## 2. Orchestration
```yaml
run_window: "{window}"
```
## 4. Budgets
```yaml
budgets: {{build_attempts: 3, review_cycles: 2, minutes_per_issue: 5, hours_per_run: 8}}
billing: {{mode: subscription}}
```
## 5. Circuit breakers
```yaml
breakers: {{consecutive_terminal_failures: 3}}
```
## 6. Merge policy
```yaml
merge: {{target: DEV, required_checks: [ci-tests, reviewer-approval], bot_identity: shim-bot}}
```
## 12. Escalation
```yaml
escalation: {{classes: [spec-conflict, ambiguity, budget, infra, security, review-deadlock], scheduling: park-and-continue}}
```
"""


def mkproj(issues, scenario=None, level="L2", window="00:00-24:00", bot="shim-bot"):
    proj = tempfile.mkdtemp(prefix="vrun-")
    os.makedirs(os.path.join(proj, ".vector"))
    os.makedirs(os.path.join(proj, ".shim"))
    with open(os.path.join(proj, "POLICY.md"), "w") as fh:
        fh.write(POLICY_TMPL.format(level=level, window=window))
    with open(os.path.join(proj, ".vector", "issues.json"), "w") as fh:
        json.dump(issues, fh)
    with open(os.path.join(proj, ".shim", "scenario.json"), "w") as fh:
        json.dump({"issues": scenario or {}, "pr_counter": 0, "pr_map": {}}, fh)
    with open(os.path.join(proj, ".shim", "config.json"), "w") as fh:
        json.dump({"bot": bot,
                   "required_checks": ["ci-tests", "reviewer-approval"]}, fh)
    return proj


def setenv():
    os.environ["VECTOR_CLAUDE_BIN"] = os.path.join(SHIMS, "claude_shim.py")
    os.environ["VECTOR_GH_BIN"] = os.path.join(SHIMS, "gh_shim.py")
    os.environ["VECTOR_GIT_BIN"] = os.path.join(SHIMS, "git_shim.py")
    os.environ["VECTOR_RATELIMIT_PARK_SECS"] = "0"
    for f in os.listdir(SHIMS):
        os.chmod(os.path.join(SHIMS, f), 0o755)


def run_cli(proj, args):
    """Run the REAL cli in-process. Returns (rc, state-dict-or-None)."""
    try:
        rc = cli.main(["--cwd", proj] + args)
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 2
    spath = os.path.join(proj, ".vector", "state.json")
    st = json.load(open(spath)) if os.path.exists(spath) else None
    return rc, st


def run_sub(proj, args, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = RUNNER_DIR
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "vector_runner", "--cwd", proj] + args,
                          capture_output=True, text=True, env=env, timeout=180)


def statuses(st):
    return {k: v["status"] for k, v in st["issues"].items()}


def gh_calls(proj):
    p = os.path.join(proj, ".shim", "gh_calls.jsonl")
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def git_calls(proj):
    p = os.path.join(proj, ".shim", "git_calls.jsonl")
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def main():
    setenv()

    # ---- S1 happy path, DAG respected, L2 autonomous merges -------------------
    proj = mkproj([{"id": "A"}, {"id": "B", "deps": ["A"]}, {"id": "C"}])
    rc, st = run_cli(proj, ["start"])
    log = [l for l in st["log"] if l.endswith(":merged")]
    S("S1 happy path: all merged, deps respected",
      statuses(st) == {"A": "merged", "B": "merged", "C": "merged"}
      and log.index("A:merged") < log.index("B:merged"))
    S("E7 every autonomous merge tag is annotated AND pushed",
      ["tag", "-a", "vector/A", "-m", "merge A (PR #1)"] in git_calls(proj)
      and ["push", "origin", "vector/A"] in git_calls(proj)
      and any(c[:2] == ["pr", "merge"] for c in gh_calls(proj)))
    S("E15 digest generated at L2 with revert handles",
      os.path.exists(os.path.join(proj, ".vector", "digest"))
      and any("vector-revert vector/A" in open(os.path.join(proj, ".vector", "digest", f)).read()
              for f in os.listdir(os.path.join(proj, ".vector", "digest")) if f.endswith(".md")))
    S("E18 SESSIONS.md has one deterministic entry per merge",
      open(os.path.join(proj, "SESSIONS.md")).read().count("| PR#") == 3)

    # ---- S2 park-and-continue --------------------------------------------------
    proj = mkproj([{"id": "A"}, {"id": "B", "deps": ["A"]}, {"id": "C"},
                   {"id": "D", "deps": ["B"]}],
                  {"B": {"build": ["failed", "failed", "failed"]}})
    rc, st = run_cli(proj, ["start"])
    S("S2 park-and-continue: B escalated, D blocked, C merged, no halt",
      statuses(st)["B"] == "escalated" and statuses(st)["D"] == "blocked-by-escalation"
      and statuses(st)["C"] == "merged" and st["halted"] is None)

    # ---- S2b ambiguity: immediate, single attempt, breaker untouched ----------
    proj = mkproj([{"id": "A"}], {"A": {"build": ["blocked"]}})
    rc, st = run_cli(proj, ["start"])
    esc = open(os.path.join(proj, "ESCALATIONS.md")).read()
    S("S2b ambiguity: immediate escalation, 1 attempt, breaker untouched",
      statuses(st)["A"] == "escalated" and st["issues"]["A"]["attempts"] == 1
      and st["consecutive_failures"] == 0
      and st["issues"]["A"]["esc_reason"] == "ambiguity"
      and "which sort order" in esc.lower())

    # ---- S3 review deadlock ----------------------------------------------------
    proj = mkproj([{"id": "A"}], {"A": {"review": ["CHANGES_REQUESTED"] * 3}})
    rc, st = run_cli(proj, ["start"])
    S("S3 review deadlock: escalated on 3rd rejection",
      statuses(st)["A"] == "escalated"
      and st["issues"]["A"]["esc_reason"] == "review-deadlock"
      and st["issues"]["A"]["rejections"] == 3)

    # ---- S4 breaker ------------------------------------------------------------
    fail3 = {"build": ["failed"] * 3}
    proj = mkproj([{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}],
                  {"A": dict(fail3), "B": dict(fail3), "C": dict(fail3)})
    rc, st = run_cli(proj, ["start"])
    S("S4 breaker: halt after 3 consecutive budget failures, D untouched",
      st["halted"] == "breaker:consecutive-failures" and statuses(st)["D"] == "queued")
    rc2, st2 = run_cli(proj, ["resume"])
    S("S4b breaker halt is STICKY on resume (needs the human)",
      rc2 == 2 and st2["halted"] == "breaker:consecutive-failures")

    # ---- S5 kill/resume (sim-style: process dies after A) ----------------------
    issues5 = [{"id": "A"}, {"id": "B", "deps": ["A"]}, {"id": "C", "deps": ["B"]}]
    ref = mkproj(list(issues5))
    _, ref_st = run_cli(ref, ["start"])
    proj = mkproj(list(issues5))
    pol = policy_mod.parse(os.path.join(proj, "POLICY.md"))
    stobj = State(os.path.join(proj, ".vector", "state.json"))
    stobj.fresh([dict(i) for i in issues5], "L2", "default", pol["_fingerprint"])
    hooks = pipeline.Hooks(proj, pol, sleep=lambda s: None)
    pipeline.run_issue(stobj, pol, hooks, "A")          # ...then the process dies
    out = run_sub(proj, ["resume"])                     # resume PURELY from state.json
    st = json.load(open(os.path.join(proj, ".vector", "state.json")))
    S("S5 kill/resume: state-file resume == uninterrupted run",
      statuses(st) == statuses(ref_st) and st["level"] == "L2",
      out.stderr[-200:])

    # ---- S5b REAL SIGKILL mid-build, then resume -------------------------------
    proj = mkproj(list(issues5), {"B": {"build": ["hang", "ok"]}})
    env = dict(os.environ, PYTHONPATH=RUNNER_DIR, SHIM_HANG_SECS="40")
    p = subprocess.Popen([sys.executable, "-m", "vector_runner", "--cwd", proj, "start"],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    spath = os.path.join(proj, ".vector", "state.json")
    deadline = time.time() + 60
    while time.time() < deadline:
        if os.path.exists(spath):
            cur = json.load(open(spath))
            if cur["issues"].get("B", {}).get("status") == "building(1)":
                time.sleep(0.5)                          # let it block inside the spawn
                break
        time.sleep(0.2)
    p.send_signal(signal.SIGKILL)
    p.wait()
    out = run_sub(proj, ["resume"])
    st = json.load(open(spath))
    S("S5b SIGKILL mid-build: resume from state alone completes; killed attempt "
      "consumed budget",
      statuses(st) == {"A": "merged", "B": "merged", "C": "merged"}
      and st["issues"]["B"]["attempts"] == 2
      and "requeued-on-resume" in " ".join(st["log"]), out.stderr[-300:])

    # ---- S6 L1 shadow ----------------------------------------------------------
    proj = mkproj([{"id": "A"}, {"id": "B"}],
                  {"A": {"review": ["CHANGES_REQUESTED"], "human": ["APPROVED"]}},
                  level="L1")
    rc, st = run_cli(proj, ["start"])
    div = [s for s in st["shadow"] if s["diverged"]]
    shadow_file = json.load(open(os.path.join(proj, ".vector", "shadow.json")))
    S("S6 shadow mode: human merged, divergence 1/2 recorded, level still L1",
      statuses(st) == {"A": "merged", "B": "merged"} and len(st["shadow"]) == 2
      and len(div) == 1 and st["level"] == "L1" and len(shadow_file) == 2)
    S("E14a at L1 the runner NEVER merges (no gh pr merge issued)",
      not any(c[:2] == ["pr", "merge"] for c in gh_calls(proj)))

    # ---- S7 freeze-class -------------------------------------------------------
    proj = mkproj([{"id": "A"}, {"id": "B", "deps": ["A"]}, {"id": "C", "deps": ["A"]},
                   {"id": "D"}],
                  {"A": {"build": ["spec-conflict"]}})
    rc, st = run_cli(proj, ["start"])
    S("S7 freeze-class: spec-conflict blocking >50% remaining -> halted",
      st["halted"] == "freeze:spec-conflict" and statuses(st)["A"] == "escalated")

    # ---- E1 rate-limit = infra-pause, never a failure --------------------------
    proj = mkproj([{"id": "A"}], {"A": {"build": ["rate-limit", "ok"]}})
    rc, st = run_cli(proj, ["start"])
    S("E1 rate-limit: parked + resumed, attempt NOT consumed, breaker untouched",
      statuses(st)["A"] == "merged" and st["issues"]["A"]["attempts"] == 1
      and st["consecutive_failures"] == 0
      and any(e["kind"] == "infra-pause" for e in st["events"]))

    # ---- E2 HALT file honored at issue boundary; resume clears it --------------
    proj = mkproj([{"id": "A"}, {"id": "B"}])
    with open(os.path.join(proj, ".vector", "HALT"), "w") as fh:
        fh.write("halt\n")
    rc, st = run_cli(proj, ["start"])
    S("E2 HALT: honored at boundary, nothing ran",
      st["halted"] == "halt-file" and statuses(st) == {"A": "queued", "B": "queued"})
    rc, st = run_cli(proj, ["resume"])
    S("E2b resume clears HALT and completes",
      st["halted"] is None and statuses(st) == {"A": "merged", "B": "merged"})

    # ---- E3 hours_per_run: clean stop at boundary; explicit resume = new window -
    proj = mkproj([{"id": "A"}])
    stobj = State(os.path.join(proj, ".vector", "state.json"))
    pol = policy_mod.parse(os.path.join(proj, "POLICY.md"))
    stobj.fresh([{"id": "A"}], "L2", "default", pol["_fingerprint"])
    stobj.st["run_started_at"] = time.time() - 9 * 3600
    stobj.persist()
    rc, st = run_cli(proj, ["resume"])
    S("E3 hours_per_run: halted at boundary, nothing picked",
      st["halted"] == "budget:hours-per-run" and statuses(st)["A"] == "queued")
    rc, st = run_cli(proj, ["resume"])
    S("E3b explicit resume after hours-cap is a new run window",
      st["halted"] is None and statuses(st)["A"] == "merged")

    # ---- E4 POLICY fail-fast ----------------------------------------------------
    proj = mkproj([{"id": "A"}])
    with open(os.path.join(proj, "POLICY.md"), "w") as fh:
        fh.write("## 1. Autonomy level\n```yaml\nautonomy_level: L2\n```\n")
    rc, st = run_cli(proj, ["start"])
    S("E4 POLICY missing keys: refuses to start, no state written",
      rc == 2 and st is None)

    # ---- E5 identity gate --------------------------------------------------------
    proj = mkproj([{"id": "A"}], bot="impostor")
    rc, st = run_cli(proj, ["start"])
    S("E5 identity mismatch: gh user != bot_identity -> refuse, nothing ran",
      rc == 2 and st is None)

    # ---- E6 run_window refusal ----------------------------------------------------
    lt = time.localtime()
    closed = "01:00-02:00" if lt.tm_hour >= 3 else "13:00-14:00"
    proj = mkproj([{"id": "A"}], window=closed)
    rc, st = run_cli(proj, ["start"])
    S("E6 outside run_window: refuses to start", rc == 2 and st is None)

    # ---- E9 the level is NEVER raised ---------------------------------------------
    proj = mkproj([{"id": "A"}], level="L1")
    rc, st = run_cli(proj, ["start", "--level", "L2"])
    S("E9a --level above POLICY refused (never raise)", rc == 2 and st is None)
    proj = mkproj([{"id": "A"}, {"id": "B"}], level="L3")
    stobj = State(os.path.join(proj, ".vector", "state.json"))
    pol = policy_mod.parse(os.path.join(proj, "POLICY.md"))
    stobj.fresh([{"id": "A"}, {"id": "B"}], "L1", "default", pol["_fingerprint"])
    rc, st = run_cli(proj, ["resume"])
    S("E9b resume keeps state's L1 even though POLICY says L3 (min wins)",
      st["level"] == "L1" and len(st["shadow"]) == 2)

    # ---- E10 CI-red retries consume the SAME build budget ---------------------------
    proj = mkproj([{"id": "A"}], {"A": {"ci": ["red", "red", "red"]}})
    rc, st = run_cli(proj, ["start"])
    S("E10 CI-red exhausts build_attempts -> budget escalation, breaker fed once",
      statuses(st)["A"] == "escalated"
      and st["issues"]["A"]["esc_reason"] == "budget:build-attempts"
      and st["issues"]["A"]["attempts"] == 3 and st["consecutive_failures"] == 1)

    # ---- E11 reviewer flags the SPEC as wrong -> spec-conflict, no breaker ----------
    proj = mkproj([{"id": "A"}], {"A": {"review": ["SPEC_CONFLICT"]}})
    rc, st = run_cli(proj, ["start"])
    S("E11 reviewer spec_conflict=true -> spec-conflict escalation, breaker untouched",
      statuses(st)["A"] == "escalated"
      and st["issues"]["A"]["esc_reason"] == "spec-conflict"
      and st["consecutive_failures"] == 0)

    # ---- E8 spec-conflict re-queues ONLY after a newer /change-scope record ---------
    proj = mkproj([{"id": "A"}], {"A": {"build": ["spec-conflict", "ok"]}})
    rc, st = run_cli(proj, ["start"])
    ok_a = statuses(st)["A"] == "escalated"
    rc, st = run_cli(proj, ["resume"])           # no change-scope record yet
    ok_b = statuses(st)["A"] == "escalated"      # must NOT re-queue
    time.sleep(1.1)                              # mtime strictly newer than esc_ts
    csdir = os.path.join(proj, "docs", "change-scope")
    os.makedirs(csdir)
    with open(os.path.join(csdir, "2026-07-15-fix.md"), "w") as fh:
        fh.write("# change-scope record\n")
    rc, st = run_cli(proj, ["resume"])
    S("E8 spec-conflict return path: parked until /change-scope record, then re-queued "
      "and merged",
      ok_a and ok_b and statuses(st)["A"] == "merged"
      and "A:requeued-after-change-scope" in st["log"])

    # ---- E13 CI infra failure: retry once, then escalate infra (no breaker feed) ----
    proj = mkproj([{"id": "A"}], {"A": {"ci": ["infra", "green"]}})
    rc, st = run_cli(proj, ["start"])
    S("E13a CI infra blip: retried once, merged, attempts==1",
      statuses(st)["A"] == "merged" and st["issues"]["A"]["attempts"] == 1
      and any(e["kind"] == "ci-infra-retry" for e in st["events"]))
    proj = mkproj([{"id": "A"}], {"A": {"ci": ["infra", "infra"]}})
    rc, st = run_cli(proj, ["start"])
    S("E13b CI infra persists: escalate infra, breaker untouched",
      statuses(st)["A"] == "escalated" and st["issues"]["A"]["esc_reason"] == "infra"
      and st["consecutive_failures"] == 0)

    # ---- E14 L0: classic HITL — runner never merges ----------------------------------
    proj = mkproj([{"id": "A"}], level="L0")
    rc, st = run_cli(proj, ["start"])
    S("E14b at L0 the human merges; runner never issues gh pr merge",
      statuses(st)["A"] == "merged"
      and not any(c[:2] == ["pr", "merge"] for c in gh_calls(proj)))

    print(f"\n{PASS} passed, {FAIL} failed — "
          + ("ALL SCENARIOS PASS" if FAIL == 0 else "FAILURES PRESENT"))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
