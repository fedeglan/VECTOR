"""Deterministic digest (SPEC §2.7) — generated from state, NO LLM call.
Merges since the last digest (issue, reviewer's plain-language summary captured at
review time, cost), escalations opened, revert handles. Written to .vector/digest/<date>.md.
"""
import os
import time


def generate(st, cwd):
    ddir = os.path.join(cwd, ".vector", "digest")
    os.makedirs(ddir, exist_ok=True)
    date = time.strftime("%Y-%m-%d")
    path = os.path.join(ddir, f"{date}.md")
    marker = os.path.join(ddir, ".last")
    last = ""
    if os.path.exists(marker):
        with open(marker) as fh:
            last = fh.read().strip()

    lines = [f"# VECTOR digest — {date}", ""]
    merged = [(iid, it) for iid, it in sorted(st.issues.items())
              if it["status"] == "merged" and it.get("tag", "") > last]
    lines.append(f"## Merges ({len(merged)})")
    for iid, it in merged:
        lines.append(f"- **{iid}** PR#{it.get('pr','-')} → `{it.get('tag','-')}` "
                     f"(tokens={it.get('tokens',0)}, wall={it.get('wall_secs',0)}s)")
        if it.get("review_summary"):
            lines.append(f"  - {it['review_summary'][:300]}")
        lines.append(f"  - revert handle: `vector-revert {it.get('tag','-')}`")
    esc = [(iid, it) for iid, it in sorted(st.issues.items())
           if it["status"] == "escalated"]
    lines.append("")
    lines.append(f"## Escalations open ({len(esc)})")
    for iid, it in esc:
        lines.append(f"- **{iid}** [{it.get('esc_reason','?')}] "
                     f"{(it.get('esc_question') or it.get('esc_positions') or '')[:200]}")
    lines.append("")
    lines.append(f"halted: {st.halted or 'no'} · consecutive_failures: "
                 f"{st.st['consecutive_failures']} · level: {st.level}")

    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    if merged:
        with open(marker, "w") as fh:
            fh.write(merged[-1][1].get("tag", ""))
    return path
