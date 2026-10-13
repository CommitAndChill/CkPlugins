---
name: ck-plan-handoff
description: "Use when /plan is invoked or when planning a Ck handoff package for a later lower-tier session. Planning only; do not implement or use to execute an existing plan."
---

# ck-plan-handoff (repository wrapper)

Read and follow the [canonical CkFoundation skill](../../../Plugins/CkFoundation/.claude/skills/ck-plan-handoff/SKILL.md) in full before acting. This repository-local source takes precedence over stale global skill entries with the same name.

Resolve every relative reference in the canonical skill from its own directory under `Plugins/CkFoundation/.claude/skills/`, including `references/` files and links to sibling skills. Do not resolve them from this wrapper.
