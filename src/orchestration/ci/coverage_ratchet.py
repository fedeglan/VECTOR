#!/usr/bin/env python3
"""VECTOR CI net: coverage-ratchet (merge-time layer). Coverage may never drop.

One of the two named downstream nets for the edit-time hooks' residual gaps: a test
neutered in a way the PreToolUse hook cannot see (early-return, whole-file overwrite) still
"passes", but it stops covering code — which shows up here as a coverage drop. Deterministic,
dependency-free (stdlib only), so it runs identically in CI and in the red-team battery.

Usage (CI, webapp reference: pytest --cov produces coverage.xml):
  python3 coverage_ratchet.py --coverage-xml coverage.xml --baseline .vector/coverage-baseline
  python3 coverage_ratchet.py --coverage-percent 87.4 --baseline .vector/coverage-baseline --set-baseline
Exit 0 = coverage held or improved; exit 1 = coverage dropped or misconfigured.
"""
import sys, argparse, os, json, xml.etree.ElementTree as ET

def read_percent_from_xml(path):
    root = ET.parse(path).getroot()               # cobertura: <coverage line-rate="0.87" ...>
    lr = root.get("line-rate")
    if lr is None:
        raise ValueError("no line-rate attribute in %s (not a cobertura coverage.xml?)" % path)
    return float(lr) * 100.0

def read_percent_from_json(path):
    d = json.load(open(path))
    if isinstance(d, dict):
        if "totals" in d and "percent_covered" in d["totals"]:   # coverage.py json
            return float(d["totals"]["percent_covered"])
        for k in ("line_coverage", "percent", "total_percent", "coverage"):
            if k in d:
                return float(d[k])
    raise ValueError("no recognizable coverage field in %s" % path)

def read_baseline(path):
    if not os.path.exists(path):
        return None
    txt = open(path).read().strip()
    try:
        return float(txt)
    except ValueError:
        d = json.loads(txt)
        for k in ("line_coverage", "percent", "coverage"):
            if k in d:
                return float(d[k])
        raise ValueError("unparseable baseline %s" % path)

def write_baseline(path, pct):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    open(path, "w").write("%.4f\n" % pct)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage-xml")
    ap.add_argument("--coverage-json")
    ap.add_argument("--coverage-percent", type=float)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--tolerance", type=float, default=0.05,
                    help="float-noise slack in percentage points (default 0.05)")
    ap.add_argument("--set-baseline", action="store_true",
                    help="initialize a missing baseline, or ratchet it UP on improvement")
    a = ap.parse_args()
    try:
        if a.coverage_percent is not None:
            cur = a.coverage_percent
        elif a.coverage_xml:
            cur = read_percent_from_xml(a.coverage_xml)
        elif a.coverage_json:
            cur = read_percent_from_json(a.coverage_json)
        else:
            print("coverage-ratchet: no coverage input "
                  "(--coverage-xml / --coverage-json / --coverage-percent)", file=sys.stderr)
            return 1
    except Exception as e:
        print("coverage-ratchet: cannot read coverage: %s" % e, file=sys.stderr)
        return 1
    try:
        base = read_baseline(a.baseline)
    except Exception as e:
        print("coverage-ratchet: cannot read baseline: %s" % e, file=sys.stderr)
        return 1
    if base is None:
        if a.set_baseline:
            write_baseline(a.baseline, cur)
            print("coverage-ratchet: baseline initialized at %.2f%%" % cur)
            return 0
        print("coverage-ratchet: no baseline at %s — initialize with --set-baseline." % a.baseline,
              file=sys.stderr)
        return 1
    if cur + a.tolerance < base:
        print("coverage-ratchet: FAIL — coverage dropped %.2f%% -> %.2f%% "
              "(tolerance %.2fpp)" % (base, cur, a.tolerance), file=sys.stderr)
        return 1
    if a.set_baseline and cur > base:
        write_baseline(a.baseline, cur)
        print("coverage-ratchet: ratcheted baseline %.2f%% -> %.2f%%" % (base, cur))
    else:
        print("coverage-ratchet: OK — %.2f%% >= baseline %.2f%%" % (cur, base))
    return 0

if __name__ == "__main__":
    sys.exit(main())
