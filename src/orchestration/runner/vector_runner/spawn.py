"""claude -p invocation — one fresh process per role per issue (SPEC §2.3).

The external binary is injectable via VECTOR_CLAUDE_BIN (default: claude) so the
red-team harness can substitute a deterministic shim while the REAL runner code runs.
Nothing in the control flow is ever mocked.

Builder contract (runner-injected context, appended to the /ship-issue prompt):
the process must end its final message with one fenced json block:
  {"outcome": "pr-open|blocked|failed|spec-conflict", "pr": <int|null>,
   "branch": "<str|null>", "question": "<str|null>", "positions": "<str|null>"}
Reviewer contract (appended to /review-pr):
  {"verdict": "APPROVED|CHANGES_REQUESTED", "summary": "<plain language>",
   "blockers": ["..."], "spec_conflict": <bool>}

Rate-limit windows under billing.mode=subscription are INFRA-PAUSES (SPEC §2.2):
detected here, surfaced as outcome "rate-limited" — the pipeline parks and retries
without consuming budget and without feeding the breaker.
"""
import json
import os
import re
import subprocess

CLAUDE_BIN = lambda: os.environ.get("VECTOR_CLAUDE_BIN", "claude")  # noqa: E731

RATE_LIMIT_MARKERS = (
    "rate limit", "rate_limit", "usage limit", "limit reached",
    "overloaded", "429", "quota exceeded",
)

JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)

BUILDER_EXIT_CONTRACT = (
    "\n\n[RUNNER CONTEXT] level={level} attempt={attempt}/{max_attempts} "
    "budget_minutes={minutes}. You are a fresh headless process driven by the "
    "relay-runner. Do not wait for a human. When done (or blocked), end your FINAL "
    "message with exactly one fenced json block: "
    '{{"outcome": "pr-open|blocked|failed|spec-conflict", "pr": <pr-number-or-null>, '
    '"branch": "<branch-or-null>", "question": "<the exact decision needed, if blocked>", '
    '"positions": "<both positions, if spec-conflict>"}}. '
    "A blocked exit on genuine ambiguity is a correct outcome — never guess."
)

REVIEWER_EXIT_CONTRACT = (
    "\n\n[RUNNER CONTEXT] You are a fresh reviewer process (tier >= builder). You never "
    "see the builder's transcript. End your FINAL message with exactly one fenced json "
    'block: {{"verdict": "APPROVED|CHANGES_REQUESTED", "summary": "<one-paragraph plain '
    'language summary for the digest>", "blockers": ["<numbered blockers, if any>"], '
    '"spec_conflict": <true if the SPEC (not the code) is wrong>}}.'
)


class SpawnResult:
    def __init__(self, outcome, data=None, tokens=0, wall_secs=0.0, raw=""):
        self.outcome = outcome      # builder: pr-open|blocked|failed|spec-conflict|rate-limited
        self.data = data or {}      # the parsed exit block
        self.tokens = tokens        # efficiency ledger
        self.wall_secs = wall_secs
        self.raw = raw


FINAL_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```\s*$", re.S)


def _extract_exit_block(text):
    """The exit block must be the FINAL content of the final message — not any fenced
    block anywhere in the transcript. A builder that prints an EXAMPLE json block and
    then fails must NOT be read as a successful exit (R-SPN-04). We require the block to
    be the last non-whitespace bytes of the result."""
    if not text:
        return None
    m = FINAL_JSON_BLOCK.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _looks_rate_limited(stdout, stderr, returncode):
    if returncode == 0:
        return False
    blob = ((stdout or "") + (stderr or "")).lower()
    return any(m in blob for m in RATE_LIMIT_MARKERS)


def _run(prompt, model, cwd, timeout_secs, disallowed, max_turns):
    cmd = [
        CLAUDE_BIN(), "-p", prompt,
        "--output-format", "json",
        "--model", model,
        "--max-turns", str(max_turns),
        "--permission-mode", "acceptEdits",
    ]
    if disallowed:
        cmd += ["--disallowedTools", ",".join(disallowed)]
    import time
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout_secs)
    except subprocess.TimeoutExpired:
        return SpawnResult("failed", {"reason": "wall-time budget exceeded"},
                           wall_secs=timeout_secs)
    wall = time.time() - t0

    if _looks_rate_limited(proc.stdout, proc.stderr, proc.returncode):
        return SpawnResult("rate-limited", wall_secs=wall, raw=proc.stderr)

    # claude --output-format json => single JSON object with result + usage
    result_text, tokens = proc.stdout, 0
    try:
        envelope = json.loads(proc.stdout)
        result_text = envelope.get("result", "")
        usage = envelope.get("usage") or {}
        tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass  # non-envelope output: fall through to raw text parsing

    exit_block = _extract_exit_block(result_text)
    if proc.returncode != 0 and exit_block is None:
        return SpawnResult("failed", {"reason": f"process exit {proc.returncode}",
                                      "stderr_tail": (proc.stderr or "")[-2000:]},
                           tokens=tokens, wall_secs=wall, raw=result_text)
    return SpawnResult(None, exit_block, tokens=tokens, wall_secs=wall, raw=result_text)


def build(issue_id, model, cwd, policy, level, attempt, failure_log=None, blockers=None,
          timeout_secs=None):
    """Spawn the builder for one attempt. Returns SpawnResult with a builder outcome.
    timeout_secs is the issue's REMAINING wall budget (minutes_per_issue is per-issue,
    not per-process)."""
    prompt = f"/vector:ship-issue {issue_id}"
    if failure_log:
        prompt += f"\n\n[PREVIOUS ATTEMPT FAILURE LOG]\n{failure_log[-4000:]}"
    if blockers:
        prompt += "\n\n[REVIEWER BLOCKERS — fix on the SAME branch]\n" + \
                  "\n".join(f"{i+1}. {b}" for i, b in enumerate(blockers))
    prompt += BUILDER_EXIT_CONTRACT.format(
        level=level, attempt=attempt,
        max_attempts=policy["budgets"]["build_attempts"],
        minutes=policy["budgets"]["minutes_per_issue"])
    res = _run(prompt, model, cwd,
               timeout_secs=timeout_secs or policy["budgets"]["minutes_per_issue"] * 60,
               disallowed=policy.get("disallowed_tools_builder", ["WebFetch", "WebSearch"]),
               max_turns=int(os.environ.get("VECTOR_MAX_TURNS", "80")))
    if res.outcome in ("failed", "rate-limited"):
        return res
    block = res.data
    if not block or block.get("outcome") not in ("pr-open", "blocked", "failed", "spec-conflict"):
        res.outcome = "failed"
        res.data = {"reason": "builder emitted no valid exit block"}
        return res
    res.outcome = block["outcome"]
    return res


def review(pr_number, model, cwd, policy, timeout_secs=None):
    """Spawn the fresh reviewer. Returns SpawnResult with verdict data."""
    prompt = f"/vector:review-pr {pr_number}" + REVIEWER_EXIT_CONTRACT
    res = _run(prompt, model, cwd,
               timeout_secs=timeout_secs or policy["budgets"]["minutes_per_issue"] * 60,
               disallowed=[],  # reviewer reads specs; still no transcript access by construction
               max_turns=int(os.environ.get("VECTOR_MAX_TURNS", "80")))
    if res.outcome in ("failed", "rate-limited"):
        return res
    block = res.data
    if not block or block.get("verdict") not in ("APPROVED", "CHANGES_REQUESTED"):
        res.outcome = "failed"
        res.data = {"reason": "reviewer emitted no valid verdict block"}
        return res
    res.outcome = block["verdict"]
    return res
