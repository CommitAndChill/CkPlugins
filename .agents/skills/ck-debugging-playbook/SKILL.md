---
name: ck-debugging-playbook
description: "Use when triaging Ck build, UHT, linker, AngelScript, editor-boot, packaged-only, GC, DLL-lock, or PIE-versus-packaged failures; not for setup, profiling, or incident history."
---

# ck-debugging-playbook (repository wrapper)

Read and follow the [canonical CkFoundation skill](../../../Plugins/CkFoundation/.claude/skills/ck-debugging-playbook/SKILL.md) in full before acting. This repository-local source takes precedence over stale global skill entries with the same name.

Resolve every relative reference in the canonical skill from its own directory under `Plugins/CkFoundation/.claude/skills/`, including `references/` files and links to sibling skills. Do not resolve them from this wrapper.
