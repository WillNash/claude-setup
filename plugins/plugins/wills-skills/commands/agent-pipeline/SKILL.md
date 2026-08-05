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

You are orchestrating a structured planning pipeline. **No code should be written until this pipeline completes.** The pipeline has a hard cap of one revision cycle — it cannot loop more than twice through the Planner/Reviewer pair.

---

### Phase 1 — Parallel Research

Launch two agents in parallel (single message, two Agent tool calls):

- **Explorer**: Agent tool with `subagent_type: "will-custom-skills:explorer"`, prompt: `$ARGUMENTS`
- **Researcher**: Agent tool with `subagent_type: "will-custom-skills:researcher"`, prompt: `$ARGUMENTS`

Wait for both to complete before proceeding.

---

### Phase 2 — Initial Planning

Launch one agent:

- **Planner**: Agent tool with `subagent_type: "will-custom-skills:planner"`, prompt: `$ARGUMENTS`

Wait for it to complete before proceeding.

---

### Phase 3 — Initial Review

Launch one agent:

- **Reviewer**: Agent tool with `subagent_type: "will-custom-skills:reviewer"`, no additional prompt needed — the agent reads the context files itself.

Wait for it to complete before proceeding.

---

### Phase 4 — Present Verdict and Collect Human Input

Read `claude-context-review.md` and report the outcome to the user:

- State the verdict (**APPROVED** or **NEEDS REVISION**) clearly.
- List each flaw found (verbatim from the review).
- If **APPROVED**: inform the user that implementation can begin and ask if they'd like to proceed. **Stop here — do not run Phase 5.**
- If **NEEDS REVISION**: present the flaws, then ask the user two things:
  1. Are there any corrections or clarifications they want to add beyond what the reviewer flagged?
  2. Should you proceed with a single revision pass, or adjust the overall approach first?

Wait for the user's response before continuing. **Do not begin Phase 5 until the user has replied.**

---

### Phase 5 — Single Revision Pass (only if NEEDS REVISION)

This phase runs **at most once**. There is no Phase 6 revision.

Read `claude-context-review.md` to get the full list of flaws. Combine those with any corrections the user provided in Phase 4.

Launch one agent with the reviewer flaws and human corrections included directly in the prompt:

- **Planner (revision)**: Agent tool with `subagent_type: "will-custom-skills:planner"`, prompt:

```
$ARGUMENTS

REVISION INSTRUCTIONS — you are revising an existing plan, not writing a new one. Read the current claude-context-plan.md first, then apply ONLY the following targeted corrections. Do not rewrite sections that were not flagged.

REVIEWER FLAWS TO FIX:
[paste the full flaws list from claude-context-review.md verbatim here]

HUMAN CORRECTIONS:
[paste any corrections the user provided in Phase 4, or write "None" if the user had no additions]
```

Wait for it to complete before proceeding.

---

### Phase 6 — Final Review

Launch one agent:

- **Reviewer**: Agent tool with `subagent_type: "will-custom-skills:reviewer"`, no additional prompt needed — the agent reads the context files itself.

Wait for it to complete before proceeding.

---

### Phase 7 — Final Verdict (hard stop — no further revision cycles)

Read `claude-context-review.md` and report the outcome to the user:

- If **APPROVED**: inform the user that implementation can begin and ask if they'd like to proceed.
- If **NEEDS REVISION**: 
  - State clearly that the pipeline revision limit has been reached.
  - List the remaining unresolved flaws as **known implementation risks**.
  - Ask the user whether to: (a) proceed to implementation with these risks noted, (b) abandon the plan and re-approach the problem differently, or (c) make manual adjustments to the plan themselves before proceeding.
  - **Do not run the Planner again.** The loop ends here regardless of the verdict.

**Do not begin writing any code or making any file changes until the user explicitly confirms they want to proceed.**
