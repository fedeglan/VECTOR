#!/usr/bin/env python3
"""VECTOR CI net: diff-based test-protection (merge-time layer).

The second named downstream net for the edit-time hook's documented residuals. The
PreToolUse `test_protection.py` hook is a *keystroke* guard and cannot see: whole-file
Write overwrites, early-return neutering (assert count unchanged), a test `mv`-renamed out
of the suite, or any deletion reached through a path it did not intercept. This check reads
the PR's unified diff and FAILS on test weakening unless a signed TEST-CHANGE-JUSTIFICATION
block is present (per the frozen method: "a diff-based detector … requiring a signed
justification block"). Deterministic, stdlib-only — identical in CI and in the red-team battery.

Usage (CI, webapp reference):
  git diff --unified=0 origin/DEV...HEAD | \
    python3 test_protection_ci.py --justification-from-git origin/DEV..HEAD
Hermetic:
  python3 test_protection_ci.py --diff patch.diff --justification-file just.txt
Exit 0 = ok (no weakening, or weakening is justified); exit 1 = unjustified test weakening.

Justification block format (in the PR body, a commit message, or a NOTES file in the diff):
  TEST-CHANGE-JUSTIFICATION
  why: <one line — why the test legitimately changed>
  Signed-off-by: <reviewer>
"""
import sys, re, argparse, subprocess

TESTFILE = re.compile(r"(^|/)(tests?/|__tests__/)|(_test\.py$)|(test_[^/]*\.py$)|(\.(test|spec)\.(ts|tsx|js|jsx)$)")
TESTDEF  = re.compile(r"\bdef\s+test_|\b(?:it|test|describe)\s*\(")
ASSERT   = re.compile(r"\bassert\b|\bexpect\s*\(")
SKIP     = re.compile(r"pytest\.mark\.(?:skip|xfail)|unittest\.skip|@Disabled|\b(?:it|test|describe)\.skip\s*\(|\bxit\s*\(|\bxdescribe\s*\(")
NEUTER   = re.compile(r"^\+\s*(?:return|pass)\s*$")
JUSTIFY  = re.compile(r"TEST-CHANGE-JUSTIFICATION", re.I)
SIGNOFF  = re.compile(r"Signed-off-by:\s*\S+", re.I)
DIFFHDR  = re.compile(r"^diff --git a/(.+?) b/(.+)$")

def parse_diff(text):
    files, cur = {}, None
    for line in text.splitlines():
        m = DIFFHDR.match(line)
        if m:
            a_path, b_path = m.group(1), m.group(2)
            is_a, is_b = bool(TESTFILE.search(a_path)), bool(TESTFILE.search(b_path))
            if is_a or is_b:
                cur = a_path if is_a else b_path
                files.setdefault(cur, dict(deleted=False, renamed_out=(is_a and not is_b),
                                           add_def=0, del_def=0, add_assert=0, del_assert=0,
                                           skip_added=0, neuter=0))
            else:
                cur = None
            continue
        if cur is None:
            continue
        if line.startswith("deleted file mode"):
            files[cur]["deleted"] = True
        elif line.startswith("rename to "):
            files[cur]["renamed_out"] = not bool(TESTFILE.search(line[len("rename to "):].strip()))
        elif line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        elif line.startswith("+"):
            body = line[1:]
            files[cur]["add_def"] += len(TESTDEF.findall(body))
            files[cur]["add_assert"] += len(ASSERT.findall(body))
            if SKIP.search(body):
                files[cur]["skip_added"] += 1
            if NEUTER.match(line):
                files[cur]["neuter"] += 1
        elif line.startswith("-"):
            body = line[1:]
            files[cur]["del_def"] += len(TESTDEF.findall(body))
            files[cur]["del_assert"] += len(ASSERT.findall(body))
    return files

def weaknesses(files):
    out = []
    for path, s in files.items():
        reasons = []
        if s["deleted"]:                         reasons.append("test file deleted")
        if s["renamed_out"]:                     reasons.append("test file renamed out of the suite")
        if s["del_def"] > s["add_def"]:          reasons.append("test cases net-removed (%d removed, %d added)" % (s["del_def"], s["add_def"]))
        if s["del_assert"] > s["add_assert"]:    reasons.append("assertions net-removed (%d removed, %d added)" % (s["del_assert"], s["add_assert"]))
        if s["skip_added"]:                      reasons.append("skip/xfail marker added")
        if s["neuter"]:                          reasons.append("early return/pass neutering a test body")
        if reasons:
            out.append((path, reasons))
    return out

def has_justification(text):
    return bool(JUSTIFY.search(text) and SIGNOFF.search(text))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", help="unified diff file (default: stdin)")
    ap.add_argument("--justification-file")
    ap.add_argument("--justification-from-git", help="commit range e.g. origin/DEV..HEAD; scans commit messages")
    a = ap.parse_args()
    diff_text = open(a.diff).read() if a.diff else sys.stdin.read()
    weak = weaknesses(parse_diff(diff_text))
    if not weak:
        print("test-protection (CI): OK — no test weakening in the diff")
        return 0
    just = diff_text                              # a NOTES-file justification can live in the diff itself
    if a.justification_file:
        try: just += "\n" + open(a.justification_file).read()
        except OSError: pass
    if a.justification_from_git:
        try:
            just += "\n" + subprocess.run(["git", "log", a.justification_from_git],
                                          capture_output=True, text=True).stdout
        except Exception: pass
    if has_justification(just):
        print("test-protection (CI): test changes present but JUSTIFIED (signed block found):")
        for p, r in weak: print("  - %s: %s" % (p, "; ".join(r)))
        return 0
    print("test-protection (CI): FAIL — unjustified test weakening:", file=sys.stderr)
    for p, r in weak: print("  - %s: %s" % (p, "; ".join(r)), file=sys.stderr)
    print("Add a signed TEST-CHANGE-JUSTIFICATION block (with Signed-off-by:) to the PR or a "
          "commit message, or restore the tests.", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
