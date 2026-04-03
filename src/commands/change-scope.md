# /change-scope

Request a design change after the Design Freeze (Step 9.5).

## Usage
```
/change-scope
```

Then describe the change you want in plain language. Claude will take it from there.

## What you do — step by step

### 1. Ask the human to describe the change
If the human has not already described the change, ask:
> "What would you like to change?"

### 2. Identify the impact
Based on the change description, identify:
- Which step(s) of the VECTOR method the change affects
- Which artefact files need to be updated (PRD, views, api-spec, erd, MSDs, architecture, CLAUDE.md, CONTEXT.md)
- Which downstream artefacts are affected as a consequence

Present the impact to the human:
```
Change requested: <summary>

Affected steps: Step N, Step M
Artefacts to update:
  · docs/<file> — <why>
  · docs/<file> — <why>

Downstream consequences:
  · <consequence>

Do you want to proceed?
```

### 3. Wait for confirmation
Do not touch any file until the human explicitly confirms.

### 4. Execute the updates
For each affected artefact, in step order:
- Read the current file
- Apply the change
- Write the updated file to disk

### 5. Update CLAUDE.md and CONTEXT.md
Always update both files last to reflect any changes made to the design.

### 6. Re-confirm the design freeze
Append an updated freeze marker to CLAUDE.md:
```
DESIGN FREEZE: YES — <date> (updated: <change summary>)
```

### 7. Report to the human
```
✓ Updated: <list of files changed>
✓ Design freeze re-confirmed

Summary of changes: <one paragraph>
```
