#!/usr/bin/env python3
"""VECTOR Tier-3 hook: test protection (PreToolUse).
Blocks test deletion, skip insertion, and assertion weakening. Exit 2 = hard block.
Residual (by design): whole-file Write overwrites of tests are allowed here and
caught by the test-protection CI check at merge time (defense in depth)."""
import sys, json, re

TESTPATH = re.compile(r"(^|/)(tests?/|__tests__/)|(_test\.py$)|(test_[^/]*\.py$)|(\.(test|spec)\.(ts|tsx|js|jsx)$)")
SKIPMARK = re.compile(r"(pytest\.mark\.(skip|xfail)|unittest\.skip|@Disabled|\b(it|test|describe)\.skip\s*\(|\bxit\s*\(|\bxdescribe\s*\()")
DELCMD   = re.compile(r"\b(rm|git\s+rm|unlink)\b[^\n|;&]*((^|[\s/])tests?/|_test\.py|\.(test|spec)\.(ts|tsx|js|jsx))")

def count(rx, s): return len(re.findall(rx, s or ""))

def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name",""); ti = data.get("tool_input",{}) or {}
    if tool == "Bash":
        if DELCMD.search(ti.get("command","")):
            print("BLOCKED [test-protection]: shell deletion of a test file. Tests are protected artifacts; "
                  "removal requires a justification block + reviewer sign-off (goes through a PR, not a shell).", file=sys.stderr)
            sys.exit(2)
        sys.exit(0)
    path = ti.get("file_path","")
    if tool in ("Edit","MultiEdit") and TESTPATH.search(path or ""):
        edits = ti.get("edits") or [{"old_string": ti.get("old_string",""), "new_string": ti.get("new_string","")}]
        for e in edits:
            old, new = e.get("old_string","") or "", e.get("new_string","") or ""
            if SKIPMARK.search(new) and not SKIPMARK.search(old):
                print("BLOCKED [test-protection]: skip/xfail marker insertion into a test.", file=sys.stderr); sys.exit(2)
            if count(r"\bassert\b|\bexpect\s*\(", new) < count(r"\bassert\b|\bexpect\s*\(", old):
                print("BLOCKED [test-protection]: assertion count reduced in a test (weakening).", file=sys.stderr); sys.exit(2)
            if count(r"\bdef test_|\b(it|test)\s*\(", new) < count(r"\bdef test_|\b(it|test)\s*\(", old):
                print("BLOCKED [test-protection]: test case removed.", file=sys.stderr); sys.exit(2)
    if tool == "Write" and TESTPATH.search(path or ""):
        if SKIPMARK.search(ti.get("content","") or ""):
            print("BLOCKED [test-protection]: writing a test file containing skip markers.", file=sys.stderr); sys.exit(2)
    sys.exit(0)

if __name__ == "__main__": main()
