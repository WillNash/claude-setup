---
name: agent-pipeline
description: Orchestrates the full planning pipeline — Explorer + Researcher in parallel, then Planner, then Reviewer — before any code is written. Use this whenever a task needs a plan first.
argument-hint: <goal description>
allowed-tools: [Agent, Read, Bash]
---

# Agent Pipeline

## Input

The user's goal: $ARGUMENTS

## Instructions

You are orchestrating a structured planning pipeline using isolated agents. Each agent reads its own instructions from its definition file. **No code should be written until this pipeline completes and the Reviewer issues an APPROVED verdict.**

### Phase 1 — Parallel Research

Launch two agents in parallel (single message, two Agent tool calls):

- **Explorer**: `Read /home/devuser/.claude/plugins/wills-skills/commands/explorer.md, ignore the YAML frontmatter, and follow the instructions in the body for this goal: $ARGUMENTS`
- **Researcher**: `Read /home/devuser/.claude/plugins/wills-skills/commands/researcher.md, ignore the YAML frontmatter, and follow the instructions in the body for this goal: $ARGUMENTS`

Wait for both to complete before proceeding.

### Phase 2 — Planning

Launch one agent:

- **Planner**: `Read /home/devuser/.claude/plugins/wills-skills/commands/planner.md, ignore the YAML frontmatter, and follow the instructions in the body for this goal: $ARGUMENTS`

Wait for it to complete before proceeding.

### Phase 3 — Review

Launch one agent:

- **Reviewer**: `Read /home/devuser/.claude/plugins/wills-skills/commands/reviewer.md, ignore the YAML frontmatter, and follow the instructions in the body.`

Wait for it to complete before proceeding.

### Phase 4 — Present Verdict

Read `claude-context-review.md` and report the outcome to the user:

- State the verdict (APPROVED or NEEDS REVISION) clearly.
- Summarise any flaws found and suggested improvements.
- If APPROVED: inform the user that implementation can begin and ask if they'd like to proceed.
- If NEEDS REVISION: present the specific revisions needed and ask whether to re-run the Planner with those corrections or adjust the approach.

**Do not begin writing any code or making any file changes until the user confirms they want to proceed after an APPROVED verdict.**