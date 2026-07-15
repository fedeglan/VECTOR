#!/usr/bin/env python3
"""VECTOR Tier-3 hook: frozen-spec protection (PreToolUse).
Blocks any mutation of frozen design artifacts. Exit 2 = hard block.

Wire in the project's .claude/settings.json under hooks.PreToolUse (see hooks.json).
Reference implementation is python3 (portable; macOS ships no jq). Red-teamed: tests/redteam.py.
"""
import sys, json, re, fnmatch

FROZEN = ["docs/api-spec.yaml", "docs/erd.dbml", "docs/PRD.md", "POLICY.md",
          "docs/api-frontend-reference.yaml", "docs/research/msd_*.md", "baselines/*"]
WRITE_TOKENS = re.compile(r"(>>?|\btee\b|\bsed\s+-i|\bperl\s+-i|\bmv\b|\bcp\b|\brm\b|\btruncate\b|\bdd\b)")

def is_frozen(path):
    if not path:
        return False
    p = path.lstrip("./")
    return any(fnmatch.fnmatch(p, pat) or p == pat for pat in FROZEN)

def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        if is_frozen(ti.get("file_path", "")):
            print("BLOCKED [frozen-specs]: '%s' is a frozen design artifact. "
                  "Specs change only via /change-scope. Escalate if the spec is ambiguous."
                  % ti.get("file_path"), file=sys.stderr)
            sys.exit(2)
    elif tool == "Bash":
        cmd = ti.get("command", "")
        hit = [pat for pat in FROZEN if re.search(re.escape(pat).replace(r"\*", r"[^\s]*"), cmd)]
        if hit and WRITE_TOKENS.search(cmd):
            print("BLOCKED [frozen-specs]: shell mutation touching frozen artifact(s) %s. "
                  "Specs change only via /change-scope." % hit, file=sys.stderr)
            sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
