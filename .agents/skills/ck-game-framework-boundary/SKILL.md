---
name: ck-game-framework-boundary
description: "Use when game code would bypass CkFoundation public APIs, mutate fragments directly, add globals, copy internals, or when a game pattern may belong upstream; not for normal feature composition."
---

# ck-game-framework-boundary (repository wrapper)

Read and follow the [canonical CkFoundation skill](../../../Plugins/CkFoundation/.claude/skills/ck-game-framework-boundary/SKILL.md) in full before acting. This repository-local source takes precedence over stale global skill entries with the same name.

Resolve every relative reference in the canonical skill from its own directory under `Plugins/CkFoundation/.claude/skills/`, including `references/` files and links to sibling skills. Do not resolve them from this wrapper.
