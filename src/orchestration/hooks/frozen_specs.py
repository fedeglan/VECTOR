#!/usr/bin/env python3
"""VECTOR Tier-3 hook: frozen-spec protection (PreToolUse).
Blocks any mutation of frozen design artifacts. Exit 2 = hard block.

Wire in the project's .claude/settings.json under hooks.PreToolUse (see hooks.json).
Reference implementation is python3 (portable; macOS ships no jq). Red-teamed: tests/redteam.py,
tests/redteam2.py, tests/redteam3.py.

Path handling: Claude Code's Edit/Write/MultiEdit tools pass an ABSOLUTE file_path, while the
frozen patterns below are repo-relative. Every incoming path is therefore normalized to a
repo-relative path (against CLAUDE_PROJECT_DIR / the hook payload's cwd) BEFORE matching, so an
absolute path can never slip past the anchored patterns. (Before v2 hardening the hook matched
only literal repo-relative paths and failed OPEN on the absolute paths a live session sends.)
"""
import sys, json, re, fnmatch, os

FROZEN = ["docs/api-spec.yaml", "docs/erd.dbml", "docs/PRD.md", "POLICY.md", "docs/views.md",
          "docs/api-frontend-reference.yaml", "docs/research/msd_*.md", "baselines/*"]
WRITE_TOKENS = re.compile(r"(>>?|\btee\b|\bsed\s+-i|\bperl\s+-i|\bmv\b|\bcp\b|\brm\b|\btruncate\b|\bdd\b)")

def project_root(data):
    """The project dir the frozen patterns are relative to. CLAUDE_PROJECT_DIR is what the
    settings.json hook wiring itself uses; the payload's cwd and the process cwd are fallbacks."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or (data or {}).get("cwd") or os.getcwd()

def rel_to_root(path, root):
    """Normalize an absolute-or-relative file_path to a repo-relative POSIX path."""
    if not path:
        return ""
    ap = path if os.path.isabs(path) else os.path.join(root, path)
    try:
        rel = os.path.relpath(os.path.normpath(ap), os.path.normpath(root))
    except ValueError:                      # e.g. different drive on Windows
        rel = os.path.normpath(ap)
    return rel.replace(os.sep, "/")

def is_frozen(path, root):
    rel = rel_to_root(path, root)
    if not rel:
        return False
    return any(fnmatch.fnmatch(rel, pat) or rel == pat for pat in FROZEN)

def change_scope_open(root):
    """/change-scope opens the ONE sanctioned mutation window by creating this marker; it removes
    it when done. While open, frozen-spec edits are permitted here — and are still gated at merge
    time by CODEOWNERS review on the frozen paths (defense in depth). Without the marker (the normal
    state, and every red-team payload), frozen specs remain uneditable."""
    try:
        return os.path.exists(os.path.join(root, ".vector", "change-scope-open"))
    except Exception:
        return False

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                         # unparseable payload: do not obstruct (never crash to exit 1)
    root = project_root(data)
    if change_scope_open(root):
        sys.exit(0)                         # sanctioned /change-scope window open; CODEOWNERS backstops the merge
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        if is_frozen(ti.get("file_path", ""), root):
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
