# /report-bug

Report a bug or improvement you found during exploratory testing. Claude Code captures it in a structured format, asks for anything missing, and adds it to the bug backlog.

## Usage

Run this command and Claude Code will ask you for the details — or paste a quick description and Claude will structure it.

```
/report-bug
```

Or shortcut form:
```
/report-bug The reports page crashes when I click "Retry" on a failed report
```

Or quick mode for rapid-fire reporting:
```
/report-bug -q "Login button misaligned on mobile" P3 V01
/report-bug -q "Export button does nothing on Portfolio page" P1 V11
/report-bug -q "Add dark mode" IMP
```

## What you do — step by step

### 1. Capture what the human said

Parse their input. Identify what's already provided vs. what needs to be asked.

### 2. Ask for missing fields

Ask in a single message, grouped. Skip anything already clear from context.

**Fields:**

1. **Title** — short, specific (e.g., "App crashes when clicking Retry on failed report")
2. **Where** — which view/page (e.g., "Reports list view, V03")
3. **Role** — which user role (admin / manager / analyst)
4. **Steps to reproduce** — numbered list, as specific as possible
5. **Expected behavior** — what the human thought would happen
6. **Actual behavior** — what actually happened (include error message if visible)
7. **Severity** — one of:
   - `P0` (blocker: can't use app)
   - `P1` (major: feature broken)
   - `P2` (minor: annoying but workable)
   - `P3` (cosmetic/polish)
   - `IMP` (improvement, not a bug)
8. **Screenshot/video** (optional) — file path or "none"

### 3. Infer intelligently to reduce friction

Don't ask for what you can figure out.

**Example 1:**
> Human: `/report-bug The PDF doesn't open on the macro report`

Infer:
- Title: "PDF does not open on Macro Report page"
- Where: Macro Report detail view (probably V06 based on views.md)
- Steps: "1. Open a Macro Report / 2. Click 'See Full Report' / 3. PDF does not load"
- Expected: "PDF opens in modal"
- Actual: "PDF does not open"

Ask only: "What role were you using, and is there an error message or a blank modal?"

**Example 2:**
> Human: `/report-bug The sidebar looks weird on mobile`

This is vague. Ask:
- "Which view? (Dashboard, Reports, Cases, etc.)"
- "Weird how? Cut off, overlapping, not scrollable, wrong color?"
- "Severity — unusable on mobile, or just cosmetic?"

### 4. Severity guidance

If the human is unsure about severity, explain:

- **P0 (blocker)**: You cannot use the app at all. Login broken, all pages 500.
- **P1 (major)**: Core feature broken. Can't approve a case. Report never completes.
- **P2 (minor)**: Feature works but with issues. Wrong sort order, slow loading, confusing UX.
- **P3 (cosmetic)**: Visual polish. Misaligned text, off-brand colors, minor typos.
- **IMP (improvement)**: Not a bug — a suggestion. "It would be better if..."

The human decides severity. Do not override their judgment.

### 5. Write to the backlog

Append to `docs/testing/BUG_BACKLOG.md`. If the file doesn't exist, create it with this header:

```markdown
# Bug Backlog

Bugs and improvements reported during human testing.

**Status legend:**
- 🟡 open — just reported, not yet triaged
- 🔵 triaged — analyzed and prioritized (by /fix-bugs analysis phase)
- 🟢 fixed — resolved and merged
- ⚫ wontfix — declined or duplicate

---
```

Then append the new bug:

```markdown
## BUG-<NNN>: <title>
**Status**: 🟡 open
**Reported**: <YYYY-MM-DD HH:MM>
**Phase**: <current phase from SESSIONS.md>
**Severity**: <P0 | P1 | P2 | P3 | IMP>
**Where**: <view name + path>
**Role**: <user role when encountered>

### Steps to reproduce
1. <step>
2. <step>
3. <step>

### Expected
<what should happen>

### Actual
<what actually happens>

### Environment
- Browser: <if provided>
- Resolution: <if provided>
- Screenshot: <path or "none">

### Notes
<anything else>

---
```

**ID assignment**: read existing BUG_BACKLOG.md and use the next sequential number. Start at `BUG-001` if none exist.

### 6. Confirm capture

```
🐛 BUG-<NNN> captured

Title: <title>
Severity: <P0-P3 or IMP>
Status: 🟡 open (awaiting analysis)

Added to: docs/testing/BUG_BACKLOG.md

Keep testing. When you're done for this session, run /fix-bugs to analyze and resolve the backlog.
```

### 7. Multiple bugs in one session

The human may run `/report-bug` many times. Each call appends to the backlog. No analysis happens until `/fix-bugs` is run explicitly.

## Quick mode parsing

For the `-q` shortcut, parse: `-q "<title>" <severity> <view?>`

Example:
```
/report-bug -q "Reports table sort reversed" P2 V03
```

Capture with minimal info: title, severity, view. Mark the bug as "needs details" so `/fix-bugs` knows to enrich it during analysis.

```markdown
## BUG-<NNN>: Reports table sort reversed
**Status**: 🟡 open (quick mode — needs details)
**Reported**: <timestamp>
**Severity**: P2
**Where**: V03 (Reports list)

### Notes
Captured in quick mode. Details to be gathered during /fix-bugs analysis.

---
```
