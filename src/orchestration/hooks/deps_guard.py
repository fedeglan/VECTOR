#!/usr/bin/env python3
"""VECTOR Tier-3 hook: dependency guard (PreToolUse).
Lockfiles/manifests are frozen at Step 12. Any addition/upgrade escalates. Exit 2 = block."""
import sys, json, re, fnmatch, shlex

MANIFESTS = ["requirements*.txt","pyproject.toml","package.json","poetry.lock",
             "package-lock.json","uv.lock","yarn.lock","Pipfile","Pipfile.lock","Gemfile*","Cargo.toml"]
ALWAYS_ADD = re.compile(r"\b(yarn\s+add|pnpm\s+add|poetry\s+add|uv\s+add|cargo\s+add|gem\s+install)\b")

def is_manifest(path):
    if not path: return False
    base = path.lstrip("./").split("/")[-1]
    return any(fnmatch.fnmatch(base, pat) for pat in MANIFESTS)

def installs_new_package(cmd):
    """Token-parse pip/npm installs: flags are skipped; -r/--requirement or bare lockfile installs pass."""
    if ALWAYS_ADD.search(cmd):
        return True
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return True  # unparseable shell -> fail closed
    for i, t in enumerate(toks):
        tail = None
        if t in ("pip","pip3") and i+1 < len(toks) and toks[i+1] == "install":
            tail = toks[i+2:]
        elif t == "uv" and toks[i+1:i+3] == ["pip","install"]:
            tail = toks[i+3:]
        elif t == "npm" and i+1 < len(toks) and toks[i+1] in ("install","i"):
            tail = toks[i+2:]
        if tail is None:
            continue
        j = 0
        while j < len(tail):
            tok = tail[j]
            if tok in ("-r","--requirement"):
                return False            # pinned install
            if tok.startswith("-"):
                j += 1; continue        # skip flags (--upgrade, --save-dev, -D, ...)
            if tok in (".","-e"):
                j += 1; continue
            return True                 # first non-flag token = a package -> addition
        return False                    # bare npm install (lockfile) / pip install with only flags
    return False

def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name",""); ti = data.get("tool_input",{}) or {}
    if tool in ("Edit","Write","MultiEdit") and is_manifest(ti.get("file_path","")):
        print("BLOCKED [deps-guard]: dependency manifests are pinned at Step 12. "
              "Adding/upgrading a dependency requires escalation (/escalate), never silent adoption.", file=sys.stderr)
        sys.exit(2)
    if tool == "Bash" and installs_new_package(ti.get("command","")):
        print("BLOCKED [deps-guard]: shell command installs a new package. "
              "Pinned installs (pip install -r, npm ci, bare npm install) are allowed; additions escalate.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__": main()
