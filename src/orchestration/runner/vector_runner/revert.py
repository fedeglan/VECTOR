"""vector-revert <tag> — a revert PR through the SAME gate sequence (SPEC §2.6).
Never a force-push. The revert PR re-enters §2.3 steps 3-6: CI wait -> fresh review ->
reviewer-approval status -> merge + its own annotated tag.
"""
import subprocess

from . import gates, spawn
from .policy import reviewer_model


class RevertError(Exception):
    pass


def _git(args, cwd):
    proc = subprocess.run([gates.GIT()] + args, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RevertError(f"git {' '.join(args)}: {proc.stderr[-400:]}")
    return proc.stdout.strip()


def run(tag, cwd, policy):
    """Open + drive the revert PR through gates. Returns (pr, new_tag)."""
    dev = policy["merge"]["target"]
    commit = _git(["rev-list", "-n", "1", tag], cwd)
    short = tag.split("/")[-1]
    branch = f"revert/{short}"

    _git(["checkout", dev], cwd)
    _git(["pull", "origin", dev], cwd)
    _git(["checkout", "-b", branch], cwd)
    try:  # merge commit first (-m 1), plain commit as fallback
        _git(["revert", "--no-edit", "-m", "1", commit], cwd)
    except RevertError:
        _git(["revert", "--no-edit", commit], cwd)
    _git(["push", "-u", "origin", branch], cwd)

    rc, out, err = gates._gh(["pr", "create", "--base", dev, "--head", branch,
                              "--title", f"revert: {tag}",
                              "--body", f"Scripted revert of `{tag}` via vector-revert. "
                                        f"Passes through the same gate sequence."], cwd)
    if rc != 0:
        raise RevertError(f"gh pr create failed: {err[-400:]}")
    pr = out.strip().rstrip("/").split("/")[-1]

    # SPEC §2.3 steps 3-6 for the revert PR
    ci_state, names, _ = gates.wait_ci(pr, cwd, policy["merge"]["required_checks"],
                                       timeout_secs=policy["budgets"]["minutes_per_issue"] * 60)
    if ci_state != "green":
        raise RevertError(f"revert PR {pr} CI not green: {ci_state} {names}")
    rres = spawn.review(pr, reviewer_model("sonnet"), cwd, policy)
    if rres.outcome != "APPROVED":
        raise RevertError(f"revert PR {pr} not approved: {rres.outcome} "
                          f"{rres.data.get('blockers')}")
    gates.set_reviewer_approval(pr, cwd, True, rres.data.get("summary", "revert"))
    new_tag = gates.merge_pr(pr, f"revert-{short}", cwd, dev)
    return pr, new_tag
