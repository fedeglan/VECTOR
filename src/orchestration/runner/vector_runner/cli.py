"""vector-run CLI — start | resume | status | halt, plus the vector-revert entry point.

Startup contract (SPEC §2.1): parse POLICY fail-fast; verify gh is authenticated as the
machine user; refuse to start outside run_window; load the ledger; never raise the level.
"""
import argparse
import glob
import json
import os
import sys
import time

from . import digest as digest_mod
from . import gates, pipeline, policy as policy_mod, revert as revert_mod, scheduler
from .state import State

LEVELS = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


def _die(msg, code=2):
    print(f"vector-run: {msg}", file=sys.stderr)
    sys.exit(code)


def _load_ledger(cwd):
    path = os.path.join(cwd, ".vector", "issues.json")
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        _die(f".vector/issues.json unreadable: {e}")
    items = data if isinstance(data, list) else data.get("issues", data)
    if isinstance(items, dict):
        items = list(items.values())
    for it in items:
        if "id" not in it:
            _die("ledger entry without an id — refusing to guess")
    return items


def _effective_level(policy_level, flag_level, state_level=None):
    """The dial only ever turns DOWN from here. Flag may lower POLICY; on resume the
    state's level may only be lowered by POLICY/flag, never raised."""
    lv = policy_level
    if flag_level:
        if LEVELS[flag_level] > LEVELS[policy_level]:
            _die(f"--level {flag_level} would RAISE the level above POLICY's "
                 f"{policy_level}; the runner never raises the level")
        lv = flag_level
    if state_level is not None and LEVELS[lv] > LEVELS[state_level]:
        lv = state_level  # resume can keep it lower, never push it higher
    return lv


def _window_check(pol):
    lt = time.localtime()
    now_m = lt.tm_hour * 60 + lt.tm_min
    if not policy_mod.in_run_window(pol["run_window"], now_m):
        _die(f"outside run_window {pol['run_window']} — refusing to start")


def _newest_change_scope_ts(cwd):
    records = glob.glob(os.path.join(cwd, "docs", "change-scope", "*.md"))
    if not records:
        return None
    newest = max(os.path.getmtime(p) for p in records)
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(newest))


def _phase_issues(items, phase):
    if not phase:
        return items
    return [i for i in items if i.get("phase", phase) == phase]


def _validate_dag(items, ledger):
    """Fail fast on a hostile/broken ledger: unknown dep ids and dependency cycles.
    A dep outside the run set is satisfied only if the LEDGER already records it
    merged (an earlier phase); anything else refuses to start — never guess."""
    run_ids = {i["id"] for i in items}
    ledger_status = {i["id"]: i.get("status", "queued") for i in ledger}
    for it in items:
        kept = []
        for d in it.get("deps", []):
            if d in run_ids:
                kept.append(d)
            elif ledger_status.get(d) == "merged":
                continue  # satisfied by an earlier phase
            else:
                _die(f"issue {it['id']} depends on {d!r}, which is neither in this "
                     f"phase nor merged in the ledger — refusing to start")
        it["deps"] = kept
    # cycle detection (DFS, three-color)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in run_ids}
    deps = {it["id"]: it.get("deps", []) for it in items}

    def visit(n, path):
        color[n] = GRAY
        for d in deps[n]:
            if color[d] == GRAY:
                _die(f"dependency cycle in the ledger: {' -> '.join(path + [d])}")
            if color[d] == WHITE:
                visit(d, path + [d])
        color[n] = BLACK

    for n in sorted(run_ids):
        if color[n] == WHITE:
            visit(n, [n])


def cmd_start(args):
    cwd = args.cwd
    pol = _parse_policy(cwd)
    _window_check(pol)
    _verify_identity(cwd, pol)

    st = State(os.path.join(cwd, ".vector", "state.json"))
    if st.exists():
        return _resume_common(st, pol, args, cwd)  # start = begin/continue

    ledger = _load_ledger(cwd)
    items = _phase_issues(ledger, args.phase)
    if not items:
        _die(f"no issues for phase {args.phase!r} in the ledger")
    # R-STA-11: a FRESH start requires a clean phase — no state.json AND no run-set issue
    # already advanced in the ledger. Otherwise resume (state) is the only safe entry.
    unclean = [i["id"] for i in items if i.get("status", "queued") not in ("queued",)]
    if unclean:
        _die(f"phase not clean for a fresh start — these issues carry a non-queued "
             f"ledger status: {', '.join(unclean)}. Resume from state.json, or reset "
             f"the ledger deliberately.")
    _validate_dag(items, ledger)
    level = _effective_level(pol["autonomy_level"], args.level)
    st.fresh(items, level, args.phase or "default", pol["_fingerprint"])
    print(f"vector-run: fresh start — {len(items)} issues, level {level}")
    return _run(st, pol, cwd)


def cmd_resume(args):
    cwd = args.cwd
    pol = _parse_policy(cwd)
    _window_check(pol)
    _verify_identity(cwd, pol)
    st = State(os.path.join(cwd, ".vector", "state.json"))
    if not st.exists():
        _die("no .vector/state.json to resume from")
    return _resume_common(st, pol, args, cwd)


def _resume_common(st, pol, args, cwd):
    st.load()
    st.st["level"] = _effective_level(pol["autonomy_level"],
                                      getattr(args, "level", None),
                                      state_level=st.level)
    if st.halted and (st.halted.startswith("halt") or
                      st.halted == "budget:hours-per-run"):
        # HALT-file stop and the hours_per_run boundary are CLEAN stops — an explicit
        # resume is a new run window. Breakers/freezes stay sticky below.
        st.st["halted"] = None
        st.st["run_started_at"] = time.time()
        halt_file = os.path.join(cwd, ".vector", "HALT")
        if os.path.exists(halt_file):
            os.remove(halt_file)
    if st.halted:
        _die(f"run is halted ({st.halted}) — a breaker/freeze needs the human; "
             f"clear state.halted deliberately after resolving it")
    requeued = scheduler.requeue_spec_conflicts(
        st, lambda: _newest_change_scope_ts(cwd))
    if requeued:
        print(f"vector-run: re-queued after /change-scope: {', '.join(requeued)}")
    inflight = scheduler.requeue_in_flight(st)
    if inflight:
        print(f"vector-run: re-queued in-flight (budgets preserved): {', '.join(inflight)}")
    st.persist()
    print(f"vector-run: resume — level {st.level}")
    return _run(st, pol, cwd)


def _run(st, pol, cwd):
    hooks = pipeline.Hooks(cwd, pol)
    final = pipeline.run(st, pol, hooks)
    if st.level in ("L2", "L3"):
        digest_mod.generate(st, cwd)  # mandatory at L2; recommended-on default at L3
    counts = {}
    for it in final["issues"].values():
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    print(f"vector-run: done — {counts}; halted={final['halted']}")
    return 0 if not final["halted"] else 1


def _parse_policy(cwd):
    try:
        return policy_mod.parse(os.path.join(cwd, "POLICY.md"))
    except policy_mod.PolicyError as e:
        _die(str(e))


def _verify_identity(cwd, pol):
    try:
        gates.verify_identity(cwd, pol["merge"]["bot_identity"])
    except gates.GateError as e:
        _die(str(e))


def cmd_status(args):
    st = State(os.path.join(args.cwd, ".vector", "state.json"))
    if not st.exists():
        print("no state — nothing running or resumable")
        return 0
    st.load()
    print(f"phase={st.st.get('phase')} level={st.level} halted={st.halted} "
          f"consecutive_failures={st.st['consecutive_failures']}")
    for iid, it in sorted(st.issues.items()):
        extra = f" [{it.get('esc_reason')}] {it.get('esc_question','')[:80]}" \
            if it["status"] == "escalated" else ""
        print(f"  {iid:10} {it['status']:24} attempts={it['attempts']} "
              f"rejections={it['rejections']}{extra}")
    return 0


def cmd_halt(args):
    path = os.path.join(args.cwd, ".vector", "HALT")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(f"halt requested {time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n")
    print("HALT written — stops at the next issue boundary")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vector-run")
    ap.add_argument("--cwd", default=".", help="project root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start")
    p.add_argument("--phase", default=None)
    p.add_argument("--level", choices=list(LEVELS), default=None)
    p.set_defaults(fn=cmd_start)
    p = sub.add_parser("resume")
    p.add_argument("--level", choices=list(LEVELS), default=None)
    p.set_defaults(fn=cmd_resume)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("halt").set_defaults(fn=cmd_halt)
    args = ap.parse_args(argv)
    args.cwd = os.path.abspath(args.cwd)
    return args.fn(args)


def main_revert(argv=None):
    ap = argparse.ArgumentParser(prog="vector-revert")
    ap.add_argument("tag")
    ap.add_argument("--cwd", default=".")
    args = ap.parse_args(argv)
    cwd = os.path.abspath(args.cwd)
    pol = _parse_policy(cwd)
    _verify_identity(cwd, pol)
    try:
        pr, tag = revert_mod.run(args.tag, cwd, pol)
    except revert_mod.RevertError as e:
        _die(str(e))
    print(f"vector-revert: PR #{pr} merged through the gates; new tag {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
