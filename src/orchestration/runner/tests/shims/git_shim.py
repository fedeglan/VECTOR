#!/usr/bin/env python3
"""Deterministic `git` shim — records every call to <cwd>/.shim/git_calls.jsonl and
succeeds. `rev-list -n 1 <tag>` prints a fixed sha for the revert flow."""
import json
import os
import sys


def main():
    args = sys.argv[1:]
    with open(os.path.join(os.getcwd(), ".shim", "git_calls.jsonl"), "a") as fh:
        fh.write(json.dumps(args) + "\n")
    if args[:2] == ["rev-list", "-n"]:
        print("cafebabecafebabe")
    elif args[:2] == ["tag", "-l"]:
        pass  # no persisted tags in the shim: report "does not exist" -> caller creates
    return 0


if __name__ == "__main__":
    sys.exit(main())
