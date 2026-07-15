"""Everything that goes through `gh`/`git` — CI polling, reviewer-approval status,
merge + annotated tag (pushed), issue close, identity check.

VECTOR_GH_BIN / VECTOR_GIT_BIN are injectable for the deterministic harness; the
default is the real binaries. The runner never force-pushes anything, anywhere.
"""
import json
import os
import subprocess
import time

GH = lambda: os.environ.get("VECTOR_GH_BIN", "gh")    # noqa: E731
GIT = lambda: os.environ.get("VECTOR_GIT_BIN", "git")  # noqa: E731


class GateError(Exception):
    pass


def _gh(args, cwd, timeout=120):
    proc = subprocess.run([GH()] + args, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def _git(args, cwd, timeout=120):
    proc = subprocess.run([GIT()] + args, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout)
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} failed: {proc.stderr[-500:]}")
    return proc.stdout


def verify_identity(cwd, bot_identity):
    """Startup check (SPEC §2.1): gh must be authenticated as the machine user."""
    rc, out, err = _gh(["api", "user", "-q", ".login"], cwd)
    if rc != 0:
        raise GateError(f"gh not authenticated: {err[-300:]}")
    login = out.strip()
    if login != bot_identity:
        raise GateError(
            f"gh authenticated as {login!r} but POLICY merge.bot_identity is "
            f"{bot_identity!r} — refusing to start (identity is a gate, not a hint)")
    return login


def ci_status(pr, cwd, required_checks):
    """Poll one round of PR checks. Returns (state, failed_names, log_tail):
    state in {green, red, infra-red, pending}. reviewer-approval is excluded —
    the runner itself sets it after the review step."""
    rc, out, err = _gh(["pr", "checks", str(pr), "--json", "name,state,link"], cwd)
    if rc != 0:
        # `gh pr checks` exits 8 while checks are pending on some versions; treat
        # unparseable/errored listing as pending unless it repeats (caller counts).
        try:
            checks = json.loads(out)
        except (json.JSONDecodeError, TypeError, ValueError):
            return "pending", [], (err or out)[-500:]
    else:
        checks = json.loads(out) if out.strip() else []
    wanted = [c for c in checks if c.get("name") in required_checks
              and c.get("name") != "reviewer-approval"]
    if not wanted:
        return "pending", [], "no required checks reported yet"
    states = {c["name"]: (c.get("state") or "").upper() for c in wanted}
    failed = [n for n, s in states.items() if s in ("FAILURE", "FAILED")]
    infra = [n for n, s in states.items() if s in ("ERROR", "CANCELLED", "TIMED_OUT", "STALE")]
    pending = [n for n, s in states.items()
               if s in ("PENDING", "QUEUED", "IN_PROGRESS", "EXPECTED", "")]
    if failed:
        return "red", failed, ""
    if infra:
        return "infra-red", infra, ""
    if pending:
        return "pending", pending, ""
    return "green", [], ""


def wait_ci(pr, cwd, required_checks, timeout_secs, poll_secs=20):
    """Block until CI concludes or times out. Timeout -> infra-red (retry-once rule)."""
    t0 = time.time()
    while time.time() - t0 < timeout_secs:
        state, names, tail = ci_status(pr, cwd, required_checks)
        if state in ("green", "red", "infra-red"):
            return state, names, tail
        time.sleep(poll_secs)
    return "infra-red", ["ci-timeout"], "CI did not conclude within the issue budget"


def failure_log(pr, cwd):
    """The failure evidence attached to the next attempt — the status rollup (names,
    conclusions, details URLs), NOT a re-poll of pr-checks (polling is wait_ci's job)."""
    rc, out, _ = _gh(["pr", "view", str(pr), "--json", "statusCheckRollup"], cwd)
    return out[-4000:] if rc == 0 else ""


def set_reviewer_approval(pr, cwd, success, summary=""):
    """Set the reviewer-approval status check on the PR's head SHA (bot identity)."""
    rc, out, err = _gh(["pr", "view", str(pr), "--json", "headRefOid,headRepository,headRepositoryOwner"], cwd)
    if rc != 0:
        raise GateError(f"cannot resolve PR {pr} head: {err[-300:]}")
    head = json.loads(out)
    sha = head["headRefOid"]
    rc, out, err = _gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], cwd)
    if rc != 0:
        raise GateError(f"cannot resolve repo: {err[-300:]}")
    repo = out.strip()
    state = "success" if success else "failure"
    rc, out, err = _gh([
        "api", f"repos/{repo}/statuses/{sha}", "-f", f"state={state}",
        "-f", "context=reviewer-approval",
        "-f", f"description={(summary or state)[:130]}",
    ], cwd)
    if rc != 0:
        raise GateError(f"failed to set reviewer-approval: {err[-300:]}")


def verify_pr(pr, iid, cwd, target_branch, bot_identity):
    """R-SPN-08: a builder-reported PR is trusted only if it genuinely belongs to this
    issue — the PR exists, its base is the target (DEV) branch, its head branch names
    this issue, and it was opened by the machine user. Returns (ok, reason)."""
    rc, out, err = _gh(["pr", "view", str(pr), "--json",
                        "number,baseRefName,headRefName,author,state"], cwd)
    if rc != 0:
        return False, f"PR {pr} not found: {err[-200:]}"
    try:
        d = json.loads(out)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False, f"PR {pr} metadata unparseable"
    if d.get("baseRefName") != target_branch:
        return False, (f"PR {pr} base is {d.get('baseRefName')!r}, not the target "
                       f"{target_branch!r}")
    # head branch must reference this issue's T-number (feat/T007-… for T007I1)
    tnum = iid.split("I")[0] if "I" in iid else iid
    head = d.get("headRefName") or ""
    if tnum.lower() not in head.lower():
        return False, f"PR {pr} head {head!r} does not name issue {iid} ({tnum})"
    author = (d.get("author") or {}).get("login")
    if bot_identity and author and author != bot_identity:
        return False, f"PR {pr} opened by {author!r}, not the machine user {bot_identity!r}"
    return True, "ok"


def pr_state(pr, cwd):
    rc, out, _ = _gh(["pr", "view", str(pr), "--json", "state"], cwd)
    if rc != 0:
        return None
    try:
        return json.loads(out).get("state")
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def do_merge(pr, cwd, dev_branch):
    """Merge if not already merged (idempotent — a resumed run must not double-merge).
    Returns 'merged' | 'already'. Raises GateError only on a genuine merge failure."""
    if pr_state(pr, cwd) == "MERGED":
        _git(["checkout", dev_branch], cwd)
        _git(["pull", "origin", dev_branch], cwd)
        return "already"
    rc, out, err = _gh(["pr", "merge", str(pr), "--merge", "--delete-branch"], cwd)
    if rc != 0:
        if pr_state(pr, cwd) == "MERGED":     # race: it merged despite the non-zero rc
            _git(["checkout", dev_branch], cwd)
            _git(["pull", "origin", dev_branch], cwd)
            return "already"
        raise GateError(f"merge failed for PR {pr}: {err[-500:]}")
    _git(["checkout", dev_branch], cwd)
    _git(["pull", "origin", dev_branch], cwd)
    return "merged"


def close_issue(gh_issue, pr, cwd):
    if gh_issue:
        _gh(["issue", "close", str(gh_issue), "--reason", "completed",
             "--comment", f"Completed in PR #{pr}"], cwd)


def tag_exists(tag, cwd):
    proc = subprocess.run([GIT(), "tag", "-l", tag], cwd=cwd, capture_output=True,
                          text=True)
    return proc.returncode == 0 and tag in proc.stdout.split()


def tag_merge(iid, pr, cwd):
    """Annotated tag + PUSH (a rollback handle). Idempotent. Raises GateError on a
    push failure — the caller keeps the (already-completed) merge and does NOT unwind."""
    tag = f"vector/{iid}"
    if not tag_exists(tag, cwd):
        _git(["tag", "-a", tag, "-m", f"merge {iid} (PR #{pr})"], cwd)
    _git(["push", "origin", tag], cwd)  # an unpushed tag is not a rollback handle
    return tag


def merge_pr(pr, iid, cwd, dev_branch, gh_issue=None):
    """Convenience for the revert path (no write-ahead needed there): merge + tag."""
    do_merge(pr, cwd, dev_branch)
    close_issue(gh_issue, pr, cwd)
    return tag_merge(iid, pr, cwd)


def pr_merged_by_human(pr, cwd):
    """L1 shadow poll: returns ('merged'|'changes'|'open', reviews_tail)."""
    rc, out, err = _gh(["pr", "view", str(pr), "--json", "state,reviews"], cwd)
    if rc != 0:
        return "open", err[-200:]
    data = json.loads(out)
    if data.get("state") == "MERGED":
        return "merged", ""
    reviews = data.get("reviews") or []
    if any((r.get("state") == "CHANGES_REQUESTED") for r in reviews):
        return "changes", json.dumps(reviews[-1])[-500:]
    return "open", ""


def escalation_labels(gh_issue, cwd, question=""):
    if gh_issue:
        _gh(["issue", "edit", str(gh_issue), "--add-label", "needs-human"], cwd)
        _gh(["issue", "comment", str(gh_issue), "--body",
             f"Escalated by the relay-runner. Decision needed: {question or 'see ESCALATIONS.md'}"], cwd)
