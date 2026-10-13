---
name: ck-build-and-env
description: "Use when setting up a Ck engine/plugin workspace or fixing engine association, stale binaries, DLL locks, build config, module rules, or headless boot; not for failure triage."
---

# ck-build-and-env (repository wrapper)

Read and follow the [canonical CkFoundation skill](../../../Plugins/CkFoundation/.claude/skills/ck-build-and-env/SKILL.md) in full before acting. This repository-local source takes precedence over stale global skill entries with the same name.

Resolve every relative reference in the canonical skill from its own directory under `Plugins/CkFoundation/.claude/skills/`, including `references/` files and links to sibling skills. Do not resolve them from this wrapper.
