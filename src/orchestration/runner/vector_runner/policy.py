"""POLICY.md parser — fenced yaml blocks keyed by the nearest preceding `##` heading.

Per the template's declared parse strategy: the runner parses ONLY the fenced ```yaml
blocks; markdown tables are human-facing mirrors. Fail fast on missing keys (SPEC §2.1;
/run-phase: "do not improvise defaults"). Decision matrices (fix severity, model pairing)
are code — REVIEW_PAIRING below mirrors POLICY §7, the table documents it.
"""
import hashlib
import re

import yaml

# Reviewer tier >= builder tier (POLICY §7 mirror; the matrix is code).
REVIEW_PAIRING = {"haiku": "sonnet", "sonnet": "opus", "opus": "opus"}
COMPLEXITY_HIGH_REVIEWER = "opus"

# The keys the runner actually consumes. Missing any -> refuse to start.
REQUIRED = [
    ("method_version",),
    ("autonomy_level",),
    ("run_window",),
    ("budgets", "build_attempts"),
    ("budgets", "review_cycles"),
    ("budgets", "minutes_per_issue"),
    ("budgets", "hours_per_run"),
    ("billing", "mode"),
    ("breakers", "consecutive_terminal_failures"),
    ("merge", "target"),
    ("merge", "required_checks"),
    ("merge", "bot_identity"),
    ("escalation", "classes"),
    ("escalation", "scheduling"),
]

HEADING = re.compile(r"^##\s+(.+?)\s*$")


class PolicyError(Exception):
    pass


def _yaml_blocks(text):
    """Yield (nearest_heading, block_text) for every fenced ```yaml block. Line scanner —
    no multi-line regex fragility."""
    heading, buf, in_block = None, None, False
    for line in text.splitlines():
        if in_block:
            if line.strip() == "```":
                yield heading, "\n".join(buf)
                in_block, buf = False, None
            else:
                buf.append(line)
            continue
        m = HEADING.match(line)
        if m:
            heading = m.group(1)
        elif line.strip() == "```yaml":
            in_block, buf = True, []
    if in_block:
        raise PolicyError(f"POLICY.md has an unterminated yaml fence under {heading!r}")


def parse(path):
    """Return the merged policy dict from POLICY.md. Raises PolicyError (fail-fast)."""
    try:
        with open(path) as fh:
            text = fh.read()
    except OSError as e:
        raise PolicyError(f"POLICY.md unreadable: {e}")

    merged = {}
    for heading, block in _yaml_blocks(text):
        try:
            data = yaml.safe_load(block)
        except yaml.YAMLError as e:
            raise PolicyError(f"POLICY.md yaml block under {heading!r} does not parse: {e}")
        if isinstance(data, dict):
            merged.update(data)  # keys are globally unique across the template's blocks

    missing = []
    for keypath in REQUIRED:
        node = merged
        for k in keypath:
            if not isinstance(node, dict) or k not in node:
                missing.append(".".join(keypath))
                break
            node = node[k]
    if missing:
        raise PolicyError("POLICY.md missing required keys: " + ", ".join(missing))

    lv = merged["autonomy_level"]
    if lv not in ("L0", "L1", "L2", "L3"):
        raise PolicyError(f"invalid autonomy_level: {lv!r}")

    merged["_fingerprint"] = hashlib.sha256(text.encode()).hexdigest()[:12]
    return merged


def in_run_window(window, now_minutes):
    """window '08:00-24:00' (local); now_minutes = minutes since local midnight."""
    try:
        lo, hi = window.split("-")
        lo_m = int(lo.split(":")[0]) * 60 + int(lo.split(":")[1])
        hi_m = int(hi.split(":")[0]) * 60 + int(hi.split(":")[1])
    except (ValueError, AttributeError):
        raise PolicyError(f"run_window unparseable: {window!r}")
    return lo_m <= now_minutes < hi_m


def reviewer_model(builder_model, complexity_high=False):
    if complexity_high:
        return COMPLEXITY_HIGH_REVIEWER
    if builder_model not in REVIEW_PAIRING:
        raise PolicyError(f"no reviewer pairing for builder model {builder_model!r}")
    return REVIEW_PAIRING[builder_model]
