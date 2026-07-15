"""State persistence — `.vector/state.json` is authoritative and kill-safe.

The state model is byte-compatible with tests/fsm_sim.py (the executable spec):
  { level, consecutive_failures, halted, shadow[], log[], issues{ id: {status, attempts,
    rejections, deps, esc_reason, ...} } }
Live-run extras (pr, branch, tokens, wall_secs, timestamps, phase) are additive fields —
the sim's assertions still hold over the shared subset.

Persistence is atomic (tmp + os.replace) and happens after EVERY transition (SPEC §2).
"""
import json
import os
import time

STATUSES = (
    "queued", "pr-open", "ci-pending", "in-review", "changes-requested",
    "merged", "escalated", "blocked-by-escalation",
)  # plus the parametric "building(k)"


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class State:
    def __init__(self, path):
        self.path = path
        self.st = None

    # ---------- lifecycle ----------
    def fresh(self, issues, level, phase, policy_fingerprint):
        """Initialize a new run. `issues` is the ledger list (dicts with id/deps/...)."""
        self.st = {
            "phase": phase,
            "level": level,
            "consecutive_failures": 0,
            "halted": None,
            "shadow": [],
            "log": [],
            "events": [],                     # infra-pauses, cadence, halts — the audit trail
            "run_started_at": time.time(),
            "policy_fingerprint": policy_fingerprint,
            "issues": {
                i["id"]: {
                    **i,
                    "status": "queued",
                    "attempts": 0,
                    "rejections": 0,
                }
                for i in issues
            },
        }
        self.persist()
        return self.st

    def load(self):
        """Resume path — state on disk is authoritative (SPEC §2.4)."""
        with open(self.path) as fh:
            self.st = json.load(fh)
        return self.st

    def exists(self):
        return os.path.exists(self.path)

    # ---------- persistence (atomic, after EVERY transition) ----------
    def persist(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(self.st, fh, indent=1)
        os.replace(tmp, self.path)

    # ---------- transitions ----------
    def set_status(self, iid, status):
        self.st["issues"][iid]["status"] = status
        self.st["log"].append(f"{iid}:{status}")
        self.persist()

    def event(self, kind, detail=""):
        self.st["events"].append({"ts": now_iso(), "kind": kind, "detail": detail})
        self.persist()

    # ---------- views ----------
    @property
    def issues(self):
        return self.st["issues"]

    @property
    def level(self):
        return self.st["level"]

    @property
    def halted(self):
        return self.st["halted"]

    def halt(self, reason):
        self.st["halted"] = reason
        self.persist()

    def statuses(self):
        return {k: v["status"] for k, v in self.st["issues"].items()}
