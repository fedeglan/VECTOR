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


def merge_pr(pr, iid, cwd, dev_branch, gh_issue=None):
    """SPEC §2.3.6: merge, close issue, checkout DEV, annotated tag + PUSH the tag."""
    rc, out, err = _gh(["pr", "merge", str(pr), "--merge", "--delete-branch"], cwd)
    if rc != 0:
        raise GateError(f"merge failed for PR {pr}: {err[-500:]}")
    _git(["checkout", dev_branch], cwd)
    _git(["pull", "origin", dev_branch], cwd)
    if gh_issue:
        _gh(["issue", "close", str(gh_issue), "--reason", "completed",
             "--comment", f"Completed in PR #{pr}"], cwd)
    tag = f"vector/{iid}"
    _git(["tag", "-a", tag, "-m", f"merge {iid} (PR #{pr})"], cwd)
    _git(["push", "origin", tag], cwd)  # an unpushed tag is not a rollback handle
    return tag


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
