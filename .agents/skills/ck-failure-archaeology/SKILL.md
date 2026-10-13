---
name: ck-failure-archaeology
description: "Use when checking whether a Ck failure, workaround, rejected design, or stalled branch has prior history before retrying, removing, or resurrecting it."
---

# ck-failure-archaeology (repository wrapper)

Read and follow the [canonical CkFoundation skill](../../../Plugins/CkFoundation/.claude/skills/ck-failure-archaeology/SKILL.md) in full before acting. This repository-local source takes precedence over stale global skill entries with the same name.

Resolve every relative reference in the canonical skill from its own directory under `Plugins/CkFoundation/.claude/skills/`, including `references/` files and links to sibling skills. Do not resolve them from this wrapper.
