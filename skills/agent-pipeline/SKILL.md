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

You are orchestrating a structured planning pipeline. Your job is to coordinate four specialist agents in sequence and present the final verdict to the user. **No code should be written until this pipeline completes and the Reviewer issues an APPROVED verdict.**

### Phase 1 — Parallel Research (run both agents simultaneously)

Launch the **Codebase Explorer** and **External Researcher** agents in parallel using a single message with two Agent tool calls:

- **Explorer agent** (`subagent_type: Explore`): Instruct it to survey the codebase for all files, functions, patterns, and conventions relevant to the goal. Tell it to write its findings to `claude-context-explorer.md` in the project root. Pass the user's goal verbatim so it knows what to look for.

- **Researcher agent**: Instruct it to research any external APIs, libraries, or documentation relevant to the goal using WebSearch and WebFetch. Tell it to write its findings to `claude-context-researcher.md` in the project root. Pass the user's goal verbatim.

Wait for both to complete before proceeding.

### Phase 2 — Planning

Launch the **Architecture Planner** agent:

- Tell it the user's goal.
- Tell it that `claude-context-explorer.md` and `claude-context-researcher.md` are ready in the project root.
- Instruct it to read both files and produce a step-by-step implementation plan written to `claude-context-plan.md`.

Wait for it to complete before proceeding.

### Phase 3 — Review

Launch the **Plan Reviewer** agent:

- Tell it that the plan is in `claude-context-plan.md`, codebase research is in `claude-context-explorer.md`, and external research is in `claude-context-researcher.md` (if it exists).
- Instruct it to cross-reference the plan against both sources, identify flaws, and write its verdict to `claude-context-review.md`.
- Remind it: APPROVED means implementation can begin; NEEDS REVISION means the plan must be fixed first.

Wait for it to complete before proceeding.

### Phase 4 — Present Verdict

Read `claude-context-review.md` and report the outcome to the user:

- State the verdict (APPROVED or NEEDS REVISION) clearly.
- Summarise any flaws found and suggested improvements.
- If APPROVED: inform the user that implementation can begin and ask if they'd like to proceed.
- If NEEDS REVISION: present the specific revisions needed and ask whether to re-run the Planner with those corrections or adjust the approach.

**Do not begin writing any code or making any file changes until the user confirms they want to proceed after an APPROVED verdict.**
