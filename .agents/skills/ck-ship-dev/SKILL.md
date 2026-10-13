---
name: ck-ship-dev
description: "Use when publishing CK superproject and plugin work through commit, fetch, rebase, post-rebase gates, submodule pushes, pointer bumps, and dev delivery."
---

# ck-ship-dev (repository wrapper)

Read and follow the [canonical CkFoundation skill](../../../Plugins/CkFoundation/.claude/skills/ck-ship-dev/SKILL.md) in full before acting. This repository-local source takes precedence over stale global skill entries with the same name.

Resolve every relative reference in the canonical skill from its own directory under `Plugins/CkFoundation/.claude/skills/`, including `references/` files and links to sibling skills. Do not resolve them from this wrapper.
