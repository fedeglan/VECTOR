#!/usr/bin/env python3
"""Red-team battery for the two CI-layer nets (coverage-ratchet + diff-based test-protection).

These are the named downstream nets for the edit-time hooks' documented residuals; per the
method they must be executed, not asserted. Hermetic: builds synthetic diffs / coverage files
in a temp dir and runs the real scripts as subprocesses. Run: python3 redteam_ci.py."""
import os, sys, subprocess, tempfile

CI = os.path.join(os.path.dirname(__file__), "..")
TP = os.path.join(CI, "test_protection_ci.py")
CR = os.path.join(CI, "coverage_ratchet.py")

def run(args, stdin=""):
    p = subprocess.run([sys.executable] + args, input=stdin, capture_output=True, text=True)
    return p.returncode

# ---------------- diff fixtures ----------------
D_OVERWRITE = """diff --git a/tests/test_pay.py b/tests/test_pay.py
--- a/tests/test_pay.py
+++ b/tests/test_pay.py
@@ -1,2 +1,2 @@
 def test_charge():
-    assert charge(10) == 10
+    pass
"""
D_DELETE = """diff --git a/tests/test_orders.py b/tests/test_orders.py
deleted file mode 100644
--- a/tests/test_orders.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def test_a():
-    assert a
-    assert b
"""
D_SKIP = """diff --git a/tests/test_auth.py b/tests/test_auth.py
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -1,2 +1,3 @@
+@pytest.mark.skip(reason="flaky")
 def test_login():
     assert ok
"""
D_ASSERT_DROP = """diff --git a/tests/test_api.py b/tests/test_api.py
--- a/tests/test_api.py
+++ b/tests/test_api.py
@@ -1,4 +1,3 @@
 def test_x():
     assert a
-    assert b
     assert c
"""
D_RENAME_OUT = """diff --git a/tests/test_helpers.py b/lib/helpers.py
similarity index 100%
rename from tests/test_helpers.py
rename to lib/helpers.py
"""
D_EARLY_RETURN = """diff --git a/tests/test_charge.py b/tests/test_charge.py
--- a/tests/test_charge.py
+++ b/tests/test_charge.py
@@ -1,2 +1,3 @@
 def test_charge():
+    return
     assert charge(10) == 10
"""
D_NEW_TEST = """diff --git a/tests/test_new.py b/tests/test_new.py
new file mode 100644
--- /dev/null
+++ b/tests/test_new.py
@@ -0,0 +1,2 @@
+def test_new():
+    assert compute() == 5
"""
D_STRENGTHEN = """diff --git a/tests/test_auth.py b/tests/test_auth.py
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -1,2 +1,3 @@
 def test_login():
     assert ok
+    assert token_present()
"""
D_NONTEST = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,2 @@
 def charge(x):
-    assert x > 0
+    pass
"""
JUST = "TEST-CHANGE-JUSTIFICATION\nwhy: endpoint removed via /change-scope; test retired\nSigned-off-by: reviewer\n"

def tp(diff, expected, label, justification=None):
    args = [TP]
    tmp = None
    if justification is not None:
        fd, tmp = tempfile.mkstemp(); os.write(fd, justification.encode()); os.close(fd)
        args += ["--justification-file", tmp]
    code = run(args, stdin=diff)
    if tmp: os.unlink(tmp)
    return ("test_protection_ci", label, expected, code, "PASS" if code == expected else "FAIL")

def cr(label, expected, percent=None, baseline_val=None, extra=None, xml=None):
    d = tempfile.mkdtemp()
    base = os.path.join(d, "baseline")
    if baseline_val is not None:
        open(base, "w").write(str(baseline_val))
    args = [CR, "--baseline", base]
    if percent is not None: args += ["--coverage-percent", str(percent)]
    if xml is not None:
        xp = os.path.join(d, "coverage.xml"); open(xp, "w").write(xml); args += ["--coverage-xml", xp]
    if extra: args += extra
    code = run(args)
    return ("coverage_ratchet", label, expected, code, "PASS" if code == expected else "FAIL")

COBERTURA_90 = '<?xml version="1.0"?>\n<coverage line-rate="0.90" version="6.0"></coverage>\n'

def main():
    results = []
    # ---- test-protection: MUST FAIL (exit 1) — unjustified weakening ----
    results.append(tp(D_OVERWRITE,   1, "whole-file overwrite guts asserts (unjustified)"))
    results.append(tp(D_DELETE,      1, "test file deleted (unjustified)"))
    results.append(tp(D_SKIP,        1, "skip/xfail marker added (unjustified)"))
    results.append(tp(D_ASSERT_DROP, 1, "assertion net-removed (unjustified)"))
    results.append(tp(D_RENAME_OUT,  1, "test renamed OUT of the suite (unjustified) [hook residual]"))
    results.append(tp(D_EARLY_RETURN,1, "early-return neuter, assert count unchanged (unjustified) [hook residual]"))
    # ---- test-protection: MUST PASS (exit 0) ----
    results.append(tp(D_SKIP,        0, "same weakening but JUSTIFIED (signed block)", justification=JUST))
    results.append(tp(D_DELETE,      0, "deletion but JUSTIFIED (signed block)", justification=JUST))
    results.append(tp(D_NEW_TEST,    0, "adding a new test file"))
    results.append(tp(D_STRENGTHEN,  0, "strengthening a test (more asserts)"))
    results.append(tp(D_NONTEST,     0, "assert removed in NON-test source (ignored)"))
    # ---- coverage-ratchet ----
    results.append(cr("coverage dropped -> FAIL", 1, percent=80.0, baseline_val=85.0))
    results.append(cr("coverage held -> OK",      0, percent=85.0, baseline_val=85.0))
    results.append(cr("within float tolerance -> OK", 0, percent=84.98, baseline_val=85.0))
    results.append(cr("coverage improved -> OK",  0, percent=90.0, baseline_val=85.0))
    results.append(cr("missing baseline, no --set -> FAIL", 1, percent=88.0, baseline_val=None))
    results.append(cr("missing baseline + --set-baseline -> OK (init)", 0, percent=88.0, baseline_val=None, extra=["--set-baseline"]))
    results.append(cr("cobertura coverage.xml read -> OK", 0, xml=COBERTURA_90, baseline_val=85.0))

    fails = sum(1 for r in results if r[4] == "FAIL")
    w = max(len(r[1]) for r in results)
    for hook, label, exp, got, verdict in results:
        print(f"{verdict:4} | {hook:18} | {label:<{w}} | expected {exp} got {got}")
    print(f"\n{len(results)-fails}/{len(results)} passed")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
