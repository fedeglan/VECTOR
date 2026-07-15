#!/usr/bin/env python3
"""Deterministic `gh` shim. Shares <cwd>/.shim/scenario.json (ci/human queues, pr_map)
and appends every call to <cwd>/.shim/gh_calls.jsonl for assertions."""
import json
import os
import sys


def load(path):
    with open(path) as fh:
        return json.load(fh)


def save(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)


def record(args):
    with open(os.path.join(os.getcwd(), ".shim", "gh_calls.jsonl"), "a") as fh:
        fh.write(json.dumps(args) + "\n")


def pop(sc, iid, kind, default):
    q = sc["issues"].setdefault(iid, {}).setdefault(kind, [])
    return q.pop(0) if q else default


def main():
    args = sys.argv[1:]
    record(args)
    scpath = os.path.join(os.getcwd(), ".shim", "scenario.json")
    cfgpath = os.path.join(os.getcwd(), ".shim", "config.json")
    sc = load(scpath)
    cfg = load(cfgpath)

    if args[:2] == ["api", "user"]:
        print(cfg.get("bot", "shim-bot"))
        return

    if args[:2] == ["pr", "checks"]:
        pr = args[2]
        iid = sc["pr_map"].get(str(pr), "?")
        out = pop(sc, iid, "ci", "green")
        save(scpath, sc)
        state = {"green": "SUCCESS", "red": "FAILURE", "infra": "ERROR"}[out]
        checks = [{"name": n, "state": ("SUCCESS" if n != "ci-tests" else state),
                   "link": ""} for n in cfg["required_checks"]
                  if n != "reviewer-approval"]
        print(json.dumps(checks))
        return

    if args[:2] == ["pr", "view"] and "statusCheckRollup" in " ".join(args):
        print(json.dumps({"statusCheckRollup": [
            {"name": "ci-tests", "conclusion": "FAILURE",
             "detailsUrl": "https://shim/checks"}]}))
        return

    if args[:2] == ["pr", "view"] and "state,reviews" in " ".join(args):
        pr = args[2]
        iid = sc["pr_map"].get(str(pr), "?")
        human = pop(sc, iid, "human", "APPROVED")
        save(scpath, sc)
        if human == "CHANGES_REQUESTED":
            print(json.dumps({"state": "OPEN",
                              "reviews": [{"state": "CHANGES_REQUESTED"}]}))
        else:
            print(json.dumps({"state": "MERGED", "reviews": []}))
        return

    if args[:2] == ["pr", "view"]:  # headRefOid etc.
        pr = args[2]
        print(json.dumps({"headRefOid": f"deadbeef{pr}",
                          "headRepository": {"name": "repo"},
                          "headRepositoryOwner": {"login": "shim"}}))
        return

    if args[:2] == ["repo", "view"]:
        print("shim/repo")
        return

    if args[0] == "api" and args[1].startswith("repos/"):
        print("{}")  # status set
        return

    if args[:2] == ["pr", "merge"]:
        print("merged")
        return

    if args[:2] == ["pr", "create"]:
        sc["pr_counter"] += 1
        pr = sc["pr_counter"]
        sc["pr_map"][str(pr)] = "revert"
        save(scpath, sc)
        print(f"https://github.com/shim/repo/pull/{pr}")
        return

    if args[0] == "issue":
        print("{}")
        return

    sys.stderr.write(f"gh_shim: unhandled: {args}\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
