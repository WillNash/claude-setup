---
name: run-skill
description: Run any installed skill as an isolated agent with its own context. First argument is the skill name, remainder is the task. Example: /run-skill flutter-dev build a login screen with Riverpod
argument-hint: <skill-name> <task description>
allowed-tools: [Agent]
---

Launch the skill-runner agent to handle this request in an isolated context.

Use the Agent tool with:
- `subagent_type`: `"will-custom-skills:skill-runner"`
- `prompt`: `"$ARGUMENTS"`

Wait for it to complete and report the result back to the user.
