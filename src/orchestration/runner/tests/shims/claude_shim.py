#!/usr/bin/env python3
"""Deterministic `claude` shim for the runner battery. Scenario-scripted exactly like
fsm_sim.MockAgents: per-issue queues in <cwd>/.shim/scenario.json:
  {"issues": {"A": {"build": ["ok"|"failed"|"blocked"|"spec-conflict"|"rate-limit"|"hang"],
               "review": ["APPROVED"|"CHANGES_REQUESTED"|"SPEC_CONFLICT"|"fail"],
               "human": [...]}},
   "pr_counter": 0, "pr_map": {}}
The REAL runner spawns this; only the external binary is substituted."""
import json
import os
import re
import sys
import time


def load(path):
    with open(path) as fh:
        return json.load(fh)


def save(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)


def pop(sc, iid, kind, default):
    q = sc["issues"].setdefault(iid, {}).setdefault(kind, [])
    return q.pop(0) if q else default


def envelope(block):
    body = "shim transcript\n```json\n" + json.dumps(block) + "\n```"
    print(json.dumps({"result": body,
                      "usage": {"input_tokens": 100, "output_tokens": 50}}))


def main():
    prompt = ""
    for i, a in enumerate(sys.argv):
        if a == "-p" and i + 1 < len(sys.argv):
            prompt = sys.argv[i + 1]
    scpath = os.path.join(os.getcwd(), ".shim", "scenario.json")
    sc = load(scpath)

    m = re.search(r"/vector:ship-issue\s+(\S+)", prompt)
    if m:
        iid = m.group(1)
        out = pop(sc, iid, "build", "ok")
        save(scpath, sc)
        if out == "rate-limit":
            sys.stderr.write("API Error: 429 rate limit exceeded\n")
            sys.exit(1)
        if out == "hang":
            time.sleep(int(os.environ.get("SHIM_HANG_SECS", "25")))
            sys.exit(1)
        if out == "blocked":
            envelope({"outcome": "blocked", "pr": None, "branch": None,
                      "question": "Ambiguous: which sort order for results?"})
            return
        if out == "failed":
            envelope({"outcome": "failed", "pr": None, "branch": None})
            return
        if out == "spec-conflict":
            envelope({"outcome": "spec-conflict",
                      "positions": "spec says X; issue says Y"})
            return
        if out == "example-nonfinal":
            # emits a plausible EXAMPLE exit block, then MORE prose after it, then fails
            # -> there is no exit block at the END of the message (R-SPN-04 attack).
            body = ('Here is the shape I will emit:\n```json\n'
                    + json.dumps({"outcome": "pr-open", "pr": 999, "branch": "feat/x"})
                    + '\n```\nBut actually the build failed after that. No PR was opened.')
            print(json.dumps({"result": body,
                              "usage": {"input_tokens": 10, "output_tokens": 5}}))
            return
        # ok -> pr-open; reuse the issue's PR on fix cycles
        pr = None
        for p, mapped in sc["pr_map"].items():
            if mapped == iid:
                pr = int(p)
        if pr is None:
            sc["pr_counter"] += 1
            pr = sc["pr_counter"]
            sc["pr_map"][str(pr)] = iid
            save(scpath, sc)
        envelope({"outcome": "pr-open", "pr": pr, "branch": f"feat/{iid}"})
        return

    m = re.search(r"/vector:review-pr\s+(\S+)", prompt)
    if m:
        pr = m.group(1)
        iid = sc["pr_map"].get(str(pr), "?")
        if sc.get("review_sleep"):
            time.sleep(float(sc["review_sleep"]))   # charge measurable reviewer wall
        out = pop(sc, iid, "review", "APPROVED")
        save(scpath, sc)
        if out == "fail":
            sys.stderr.write("reviewer process exploded\n")
            sys.exit(1)
        if out == "SPEC_CONFLICT":
            envelope({"verdict": "CHANGES_REQUESTED", "summary": "the spec is wrong",
                      "blockers": [], "spec_conflict": True})
            return
        if out == "CHANGES_REQUESTED":
            envelope({"verdict": "CHANGES_REQUESTED",
                      "summary": "shim: found blockers",
                      "blockers": ["1. shim blocker: fix the thing"],
                      "spec_conflict": False})
            return
        envelope({"verdict": "APPROVED", "summary": f"shim: {iid} looks correct",
                  "blockers": [], "spec_conflict": False})
        return

    sys.stderr.write(f"claude_shim: unrecognized prompt: {prompt[:80]}\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
