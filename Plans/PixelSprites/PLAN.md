# Pixel sprite implementation gates

Written 2026-10-11. Gate status and evidence are recorded only in PROGRESS.md.

## Architecture

Existing CkPixelArt configures scene-wide low-resolution rendering through CkPixelArtRenderer. It is not an image format or sprite player. The independent CkPixelSprite runtime owns sprite grids, decoding, imported assets, derived textures and playback. CkPixelSpriteEditor owns import/reimport. CkPixelArtViewer belongs in the existing Plugins/CkGameplayDebugger checkout, whose descriptor is already CkDebugger.uplugin. No plugin rename is part of this work.

Dependency direction: viewer -> editor -> runtime; viewer may also use runtime directly. Runtime never depends on either editor module. Follow CkModuleRules and disable unity for the new modules. No Paper2D requirement.

## Gates

1. Investigation/design: inspect descriptors, module rules, neighboring viewers, asset integration, JSON/filesystem utilities, tests and failure conventions. Resolve architectural blockers before dependent edits.
2. Core: native XPM parser, contiguous indexed grids, manifest validation, pure time evaluator; CLI and shared fixtures can be developed independently once the supported format is fixed. Verify native automation and CLI conformance before adding UI. Invalid input must leave caller output unchanged.
3. Assets: reflected image/animation assets, atomic importer and dependency-aware reimport, Unreal-side settings preserved. Verify import, serialization/reload and rejected import/reimport without mutation. Local Development cook/package verification is explicitly authorized through Toolbox v1.61.
4. Basic viewer: native asset opening, canvas, timeline, explicit timing, pan/zoom/grid and controls. Verify registered tool and asset opening; record exact manual visual checks.
5. Advanced viewer: onion skins, comparison, palette overrides, diagnostics, persistent settings and render previews. Verify deterministic image differences and source immutability, then human visual acceptance.
6. Runtime: cached textures for each unique source and gameplay playback API, anchors, optional events. Verify lifetime, no per-frame decode/upload, BP/AS access, and locally packaged rendering through Toolbox. All source textures are prepared before playback; no lazy uploads during frame changes. An atlas is considered but deferred in favor of direct textures with bounded generation memory and no UV/packing complexity.
7. Polish: complete examples, documentation, shortcuts, export tooling, conformance and final acceptance record.

Each gate must compile the affected modules, run focused compatible tests, review fresh startup logs and record observed outcomes. A failed build caused by unrelated shared changes blocks dependent gates; preserve them and report evidence. Do not claim full implementation from a core-only gate.

## Reference patterns

- Foundation CLAUDE.md and Source/CLAUDE.md provide the published coding and module rules.
- Source/CkBuildConfig/CkBuildConfig.Build.cs owns CkModuleRules.
- Source/CkInsightsAnalyzer/Public/CkInsightsAnalyzer/Report/CkJsonReport.spec.cpp demonstrates pure native automation.
- Debugger Source/CkSmDebugger/CkSmDebugger_Module.cpp and CkEcsDebugger_Module.cpp demonstrate tab/tool registration and teardown.
- Debugger Source/CkDebuggerCommon/CLAUDE.md and CkDebuggerLauncher/CLAUDE.md own native tool authoring.

## Outstanding design verification

Native factory and asset editor signatures were inspected in the installed engine; exact references are in PROGRESS.md. The maintainer authorized engine-required raw signatures and expected malformed-source failures as ordinary structured failures in every build. Cap dimensions, source size, palettes, frame counts and aggregate pixel budget before allocation. Native core and reflected assets/importer gates now pass; current evidence and remaining acceptance are in PROGRESS.md.
