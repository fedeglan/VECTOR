# /explain-pr

Explain the PR you just made in plain, simple language. This is for the human who has 2 minutes to understand what happened before reviewing.

## What you do

Read the PR diff and the issue it closes, then produce a brief structured explanation. No jargon. No filler. Write as if explaining to a smart person who hasn't looked at the code today.

## Output format

Write exactly this structure, in chat — not as a file:

```
## What I just did

**Issue**: T<NNN>I<N> — <title>
<1 sentence: what this issue is about in plain language>

**Big picture**: This is part of <component/module/layer> which handles <purpose in the app>.
<1 sentence connecting this issue to the user-facing feature it enables>

**What I built**:
- <thing 1 — what it does, not what file it's in>
- <thing 2>
- <thing 3 if needed>

**Why this way**:
<1-2 sentences explaining the key design choice. Why this approach and not another.>

**How I know it works**:
- <test or verification 1>
- <test or verification 2>
- Checked against: <spec file and section>

**If you only have 2 minutes, look at**:
1. <file:line-range> — <why this is the critical part>
2. <file:line-range> — <why>
```

## Rules

- **No code blocks in the explanation.** File paths and line numbers are fine, but don't paste code.
- **No technical jargon without explanation.** "Repository layer" → "the part that talks to the database." "Middleware" → "the code that runs before every request." If the human knows the term, great — they'll read past it. If they don't, they won't be lost.
- **"Big picture" must connect to a user action.** Not "this implements the trade repository" but "this is the database layer for trades — without it, the portfolio page can't show holdings."
- **"If you only have 2 minutes" must be genuinely useful.** Point to the 1-2 places where a bug would actually matter. Not boilerplate, not imports, not test files — the logic that could be wrong.
- **Be honest about uncertainty.** If there's a part you're not 100% sure about, say so: "The edge case at line 47 handles empty portfolios — worth a glance."
- **Keep it under 20 lines total.** This is a speed briefing, not a report.