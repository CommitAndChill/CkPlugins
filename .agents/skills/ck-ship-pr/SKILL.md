---
name: ck-ship-pr
description: "Publish CK superproject and submodule work like ck-ship-dev, but submodules go out as feature-branch PRs for the maintainer to merge instead of direct dev pushes. Use when the user asks to ship via PRs, or when the session's maintainer has a standing PR-first preference."
---

# ck-ship-pr (repository wrapper)

Read and follow the [canonical CkFoundation skill](../../../Plugins/CkFoundation/.claude/skills/ck-ship-pr/SKILL.md) in full before acting. This repository-local source takes precedence over stale global skill entries with the same name.

Resolve every relative reference in the canonical skill from its own directory under `Plugins/CkFoundation/.claude/skills/`, including `references/` files and links to sibling skills. Do not resolve them from this wrapper.
