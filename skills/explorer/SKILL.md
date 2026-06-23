---
name: explorer
description: Targeted inline codebase exploration. Finds files, traces dependencies, and summarises findings directly in the conversation — without spawning a subprocess. Use for quick, focused lookups mid-conversation. For full pipeline research (parallel + written to file), use the agent-pipeline skill instead.
argument-hint: <what to find or understand>
allowed-tools: [Read, Glob, Bash]
---

# Codebase Explorer (inline)

## Input

$ARGUMENTS

## Instructions

You are doing a focused, read-only exploration of the codebase. No files will be modified.

1. **Locate** — use `Glob` to find files by name or pattern; use `Bash` for `grep -r` or `find` searches. Never run, build, or modify anything.
2. **Read** — open the relevant files. Trace the data flow: follow imports, function calls, and type definitions across files until you have a complete picture of the area under investigation.
3. **Report inline** — summarise your findings directly in the conversation with:
   - Which files are involved and what each one is responsible for
   - Where the specific logic, type, or function lives (file path + line number)
   - Any dependencies, side-effects, or gotchas the user should know before making changes
   - A short answer to the original question if one was asked

Keep the report concise and structured. Use a short code snippet only when it meaningfully clarifies something — don't paste large blocks. If the question is answered in two sentences, two sentences is fine.
