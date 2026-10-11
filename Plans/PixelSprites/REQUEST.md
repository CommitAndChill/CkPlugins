# Task: Implement an XPM Pixel Art & Animation Framework and Viewer for CkPlugins

## 1. Objective

Implement a complete, reusable **2D pixel art and frame-by-frame animation system** for Unreal Engine, integrated into the existing `CkFoundation` and `CkGameplayDebugger` plugins.

The primary author of the artwork will be **Codex**, not a human pixel artist.

Codex will define sprites directly as discrete 2D grids of pixels using the established **X PixMap (XPM3)** format. Animation will consist of multiple XPM frames described by a small JSON manifest.

The system must provide:

1. A robust native C++ XPM parser.
2. Support for palette-indexed pixel art.
3. Frame-based animations with explicit timing.
4. An extensible runtime rendering and playback system.
5. Unreal Engine asset import and reimport support.
6. A full-featured native Unreal Editor pixel art and animation viewer.
7. Developer tools allowing Codex to generate, inspect, validate, and modify source artwork.
8. Automated tests, examples, and documentation.

The canonical source must remain XPM + JSON. Rendering, smoothing, scaling, runtime playback, and exporting must never destructively modify the source pixels.

**Do not introduce Pixelorama, Aseprite, or another external pixel editor as a dependency.**

This is not a painting tool. Codex writes the artwork; the Unreal Editor viewer allows humans to inspect, preview, debug, and test it.

---

## 2. Existing Repository and Coding Conventions

The repository contains an established family of Unreal Engine plugins, including:

- `CkFoundation`
- `CkGameplayDebugger`
- `CkTests`
- Other `Ck*` modules and shared tooling.

`CkGameplayDebugger` will eventually be renamed to `CkTools`. Do not perform that rename as part of this task.

Before implementing anything, inspect the repository thoroughly.

### Mandatory Initial Investigation

Identify:

- `CkFoundation.uplugin` and its existing modules.
- `CkGameplayDebugger.uplugin` and its existing modules.
- Existing module Build.cs patterns and shared `CkModuleRules`.
- Existing asset types, `UFactory` implementations, asset definitions, asset editors, and custom Slate UI.
- Existing texture/image processing utilities.
- Existing JSON, serialization, and filesystem utilities.
- Existing developer tool registration and tab/window mechanisms.
- Existing test infrastructure, including `CkTests`.
- Existing allocation, assertions, logging, and error-reporting conventions.
- How modules share code without circular dependencies.
- Existing file naming and source organization conventions.

In particular, study the architecture of existing debuggers/viewers such as `CkEcsDebugger` and `CkStateMachineViewer`.

Do not invent new patterns if suitable ones already exist.

### C++ Conventions

Follow the conventions actually present in the repository.

Known preferences include:

- Use `auto` aggressively where appropriate.
- Prefer trailing return types for ordinary C++ functions, except where Unreal reflection requirements or project conventions dictate otherwise.
- Prefer early returns over deeply nested conditionals.
- Use existing `CK_ENSURE_IF_NOT`, assertion, logging, and property/accessor patterns where appropriate.
- Respect Unreal reflection, GC, and object-lifetime requirements.
- Maintain Blueprint/Angelscript compatibility where applicable and consistent with surrounding APIs.
- Keep headers self-contained.
- Use explicit module dependencies.
- Ensure all new modules compile with unity builds disabled.
- Avoid unnecessary abstraction, duplication, and dependencies.
- Avoid introducing editor-only types into runtime module public headers.

**Repository conventions take precedence over these examples.**

Do not blindly apply `CK_PROPERTY`, custom handles, ECS patterns, or other abstractions where they are unnecessary.

---

## 3. Module Architecture

Use the following proposed architecture, adjusting it only when repository investigation identifies a better fit.

### 3.1 `CkFoundation`: `CkPixelArt`

**Type:** Runtime

Responsibilities:

- XPM parsing and decoding.
- Canonical in-memory pixel-grid representation.
- Palette data and palette indices.
- Frame and animation data.
- Animation timing and playback evaluation.
- Animation metadata and anchor points.
- Imported animation asset representation.
- Runtime rendering interfaces and texture generation where appropriate.
- Animation playback components and Blueprint-facing APIs.

The runtime module must not depend on editor tooling.

### 3.2 `CkFoundation`: `CkPixelArtEditor`

**Type:** Editor

Responsibilities:

- XPM import factories.
- JSON animation manifest importing.
- Unreal asset generation.
- Reimport support.
- Source-file dependencies.
- Source validation.
- Asset registry integration.
- Editor-side image export where appropriate.
- Asset actions/definitions needed to locate and open the relevant viewer.

Do not couple this module directly to `CkGameplayDebugger`.

### 3.3 `CkGameplayDebugger`: `CkPixelArtViewer`

**Type:** Editor

Responsibilities:

- Full pixel-art preview.
- Frame-by-frame animation viewer.
- Playback controls.
- Timeline with thumbnails.
- Palette inspection.
- Pixel grid inspection.
- Onion skinning.
- Zoom and pan.
- Render-mode previews.
- Animation comparison.
- Source diagnostics.
- Frame and animation metadata.
- Export UI.
- Integration with existing Ck developer tooling.

This module should depend on the Foundation modules through clean public interfaces.

If the existing Ck tool architecture strongly favors adding the viewer to an established module rather than creating another module, follow that architecture and explain the decision.

### Dependency Direction

The intended dependency graph is:

`CkPixelArtViewer -> CkPixelArtEditor -> CkPixelArt`

The viewer may also directly depend on `CkPixelArt`.

No dependency may point back from Foundation to GameplayDebugger.

The future rename from `CkGameplayDebugger` to `CkTools` should require minimal changes, ideally limited to module descriptors and registration points.

---

## 4. Source Asset Format

### 4.1 XPM as the Authoritative Pixel Format

Use **XPM3**, the conventional C-style X PixMap text format.

Example:

```c
/* XPM */
static char *sprite[] = {
"8 8 3 1",
". c None",
"K c #343743",
"Y c #F5BD46",
"........",
"..KKKK..",
".KYYYYK.",
"KYYYYYYK",
"KYYYYYYK",
".KYYYYK",
"..KKKK..",
"........"
};
```

Each character (or sequence of characters, when characters-per-pixel exceeds one) represents a palette entry.

The importer must support:

- Arbitrary valid dimensions within configurable safety limits.
- XPM colors and transparency.
- Palette entries.
- Multiple characters per pixel.
- Case-sensitive pixel symbols.
- Standard XPM color declarations.
- Strict row-length verification.
- Palette index validation.
- Correct handling of whitespace inside pixel rows.
- Source locations in diagnostics when possible.
- UTF-8 text files containing the XPM syntax, without treating arbitrary Unicode characters as XPM pixels.

Do not implement XPM by naively splitting quoted strings.

Implement a proper parser for the supported XPM3 syntax, including safe handling of C-style string literals and escaped characters.

Unsupported or ambiguous XPM constructs should produce clear diagnostics rather than silently generating incorrect pixels.

Determine and document the supported subset of the XPM standard.

### 4.2 Internal Pixel Representation

Keep pixel data separate from its rendered color representation.

Suggested conceptual types:

- `FCkPixelPalette`
- `FCkPixelGrid`
- `FCkPixelFrame`
- `FCkPixelAnimation`
- `FCkPixelAnimationSequence`

These are illustrative names, not mandatory APIs.

Represent a frame using:

- Width and height.
- Contiguous row-major palette indices.
- Palette/color table.
- Transparency information.
- Optional metadata.

Prefer compact indices where appropriate, but account for palettes larger than 256 colors.

For example, support an adaptive index representation or a suitable integer type without unnecessary complexity.

Avoid storing individual pixels as UObjects.

Provide fast indexed access and contiguous memory access for renderers and tooling.

### 4.3 Animation Manifest

XPM is an image format, not an animation format.

Use a companion JSON manifest for animations.

Example:

```json
{
  "version": 1,
  "canvas": {
    "width": 32,
    "height": 32
  },
  "animations": {
    "idle": {
      "playback": "loop",
      "frames": [
        {
          "source": "Idle/000.xpm",
          "duration_ms": 125
        },
        {
          "source": "Idle/001.xpm",
          "duration_ms": 125
        }
      ]
    },
    "attack": {
      "playback": "once",
      "frames": [
        {
          "source": "Attack/000.xpm",
          "duration_ms": 60,
          "anchors": {
            "muzzle": [26, 12]
          }
        },
        {
          "source": "Attack/001.xpm",
          "duration_ms": 90
        }
      ]
    }
  }
}
```

Support:

- Multiple named animation sequences.
- Per-frame duration in milliseconds.
- Loop, once, and ping-pong playback.
- Explicit frame ordering.
- Stable canvas dimensions.
- Optional per-frame anchor positions.
- Optional metadata and events.
- Format versioning and validation.

Use safe relative path resolution. Reject manifest paths that escape the source asset directory.

Do not store duplicate pixel data in the manifest.

An individual XPM must remain independently importable and previewable without requiring a manifest.

### 4.4 Layers

Layer support is desirable, especially for character animations, weapons, VFX, and compositing.

However, XPM itself has no layer concept.

Design optional manifest-defined layers where each frame may reference multiple XPM sources.

Potential fields include:

- Layer name.
- Source XPM.
- Visibility.
- Opacity.
- Blend mode.
- Positional offset.
- Draw order.

Keep the implementation simple initially.

Support ordinary alpha compositing first. Do not build a general-purpose image compositor unless required.

The runtime should be able to use precomposited textures without preserving the complete layer structure in GPU memory.

---

## 5. Unreal Asset Integration

Create native Unreal assets representing imported pixel art and animations.

Suggested types:

- `UCkPixelArtAsset`
- `UCkPixelAnimationAsset`

Names may be adjusted to existing Ck conventions.

### Single-Image Import

Importing an `.xpm` file should create an appropriate pixel-art asset.

### Animation Import

Importing an animation JSON manifest should create an animation asset containing:

- Frame data or references.
- Timing.
- Named animation sequences.
- Palette information.
- Rendering metadata where appropriate.
- Source dependency information.

### Reimport

Support reimporting when any source file changes.

This includes:

- The manifest.
- Referenced XPM frames.
- Palette sources, if used.

Ensure modifications to one animation frame do not unnecessarily invalidate unrelated assets.

Where useful, maintain source hashes or dependency timestamps.

Preserve Unreal-side configuration that should survive reimport.

For example, user-selected preview settings should not disappear when a frame is modified.

### Asset Editor Opening

Double-clicking an imported pixel-art or animation asset in the Content Browser should open the custom pixel-art viewer.

Reuse existing asset-definition and toolkit infrastructure where suitable.

Do not automatically convert all frames into separate visible `UTexture2D` assets unless there is a compelling architectural reason.

Investigate transient/generated textures, cooked bulk data, and atlas representations as appropriate.

---

## 6. Native Unreal Pixel Art & Animation Viewer

Create a polished, professional viewer integrated into Unreal Editor.

Use Slate and existing Ck tool infrastructure.

Do not implement the viewer using an embedded web browser.

### 6.1 Main Layout

The viewer should contain:

**Central canvas**

A large preview area displaying the artwork or animation.

**Bottom timeline**

Frame thumbnails, frame selection, duration visualization, playback position, and animation controls.

**Left panel**

Asset information, animation sequence selection, optional layers, and source file hierarchy.

**Right panel**

Palette, rendering settings, selected-frame metadata, animation properties, and diagnostics.

Panels should be dockable/resizable if the existing Ck tooling supports this naturally.

Settings and layout preferences should persist between editor sessions.

### 6.2 Viewport

Required features:

- Pan using middle-mouse dragging.
- Zoom using the mouse wheel.
- Zoom centered on cursor.
- Fit-to-window.
- Center image.
- Reset view.
- Integer zoom presets.
- Noninteger zoom for inspection.
- Transparent checkerboard background.
- Configurable background color.
- Toggle pixel grid.
- Optional major grid lines.
- Coordinate axes.
- Pixel coordinate readout.
- Pixel color and palette index under cursor.
- Optional crosshair.
- Fullscreen or maximized preview.

All zoom operations must preserve the source image.

Nearest-neighbor rendering should maintain sharp pixels.

At very high zoom levels, individual pixels must remain visually distinct.

### 6.3 Timeline

Implement an actual animation timeline, not simply a list of frames.

Required:

- Thumbnail for every frame.
- Playhead.
- Scrubbing.
- Click-to-select frame.
- Frame numbers.
- Per-frame duration.
- Total animation duration.
- Variable-duration frames.
- Previous/next frame.
- First/last frame.
- Play/pause.
- Stop.
- Restart.
- Loop mode.
- Playback direction.
- Adjustable speed multiplier.
- Current animation time.
- Current frame index.

Frame durations must not be incorrectly normalized to a fixed FPS.

Consider displaying a proportional timeline where frames with longer durations occupy greater widths.

### 6.4 Playback

Playback must use the animation's explicit time data.

Support:

- Forward playback.
- Reverse playback.
- Loop.
- Ping-pong.
- One-shot.
- Pause/resume.
- Manual scrubbing.
- Speed multipliers such as 0.25×, 0.5×, 1×, 2×, and 4×.
- Explicit frame stepping.

Playback must not depend on Unreal Editor's frame rate being perfectly stable.

Use accumulated time rather than advancing exactly one animation frame for each editor tick.

Handle large time deltas correctly.

### 6.5 Frame Skipping Simulation

This is particularly important.

Provide a mode for previewing animations with reduced temporal fidelity.

Examples:

- Every frame.
- Every second frame.
- Every third frame.
- Effective preview rates such as 30, 15, 10, and 5 FPS.

Be precise about the semantics.

Distinguish between:

1. Source animation frames.
2. Sampling or presentation frequency.
3. Playback speed.

Reducing sampling frequency should not unintentionally accelerate the animation.

Include both fixed-interval temporal sampling and optional explicit source-frame decimation if feasible.

### 6.6 Onion Skinning

Support previous and next frame overlays.

Options:

- Enable/disable.
- Number of preceding frames.
- Number of following frames.
- Opacity.
- Different tint for preceding versus following frames.
- Respect transparency.
- Ability to display only selected surrounding frames.

The active frame must remain visually distinguishable.

### 6.7 Frame Comparison

Provide:

- Side-by-side frame comparison.
- Overlay comparison.
- Difference visualization.
- Optional difference bounding box.
- Pixel-count difference statistics.

This is useful when Codex introduces small unwanted changes between frames.

### 6.8 Palette Viewer

Display the palette as selectable swatches.

For each color, show:

- Color value.
- Source palette symbol.
- Palette index.
- Transparency.
- Usage count, if practical.

Support temporary preview palette overrides without rewriting the source.

If possible, highlight all pixels using a selected palette entry.

---

## 7. Rendering System

The canonical source is always a discrete pixel grid.

Rendering must be decoupled from source data.

### 7.1 Required Render Modes

**Nearest-neighbor**

Traditional pixel-perfect rendering with sharp square pixels.

**Bilinear**

Standard texture interpolation for comparison.

**Smooth silhouette**

A configurable mode that produces smoother external edges while preserving the underlying pixel geometry.

Do not simply label bilinear filtering as smooth silhouette rendering.

Investigate suitable methods, such as:

- Higher-resolution rasterization.
- Supersampling.
- Alpha-mask reconstruction.
- Edge-aware scaling.
- Outline-focused smoothing.

Implement a practical, deterministic initial method and explain its limitations.

Do not silently apply algorithms that create unwanted colors or destroy hard interior features.

### 7.2 Rendering Settings

Expose:

- Render mode.
- Render scale.
- Transparency handling.
- Optional outline treatment.
- Palette override.
- Optional background.
- Pixel-grid overlay (viewer only).
- Antialiasing options where relevant.

### 7.3 Runtime Output

Investigate and implement a suitable Unreal rendering path.

Possible options:

- Generated `UTexture2D` resources.
- Texture atlas plus UV coordinates.
- Material-based rendering.
- Paper2D integration, if already enabled and beneficial.

Avoid adding Paper2D as a mandatory dependency unless clearly justified.

Prefer efficient GPU-friendly playback over uploading an entire texture every frame.

A sprite sheet/atlas should be considered for animations.

Ensure the renderer supports both viewer preview and gameplay runtime.

They should share the same rendering principles and resources wherever practical.

### 7.4 Color Handling

Pay attention to:

- sRGB versus linear color.
- Alpha compositing.
- Premultiplied versus straight alpha.
- Filtering around transparent edges.
- Texture import/compression settings.
- Mipmapping.
- Pixel-perfect sampling.

Prevent unwanted halos and color bleeding around transparent pixels.

Do not allow normal Unreal texture defaults to unintentionally blur nearest-neighbor pixel art.

---

## 8. Runtime Animation System

Provide a lightweight runtime player.

Responsibilities:

- Select an animation sequence.
- Advance playback using elapsed time.
- Determine the active frame.
- Handle looping and ping-pong.
- Track playback state.
- Expose current frame and normalized time.
- Apply speed multipliers.
- Resolve frame anchors.
- Optionally emit animation events.

Design an appropriate Blueprint-accessible component if consistent with existing Ck architecture.

Do not force the animation system into the ECS unless the existing repository already provides an appropriate integration pattern.

The core playback evaluator should ideally be independent of UObject lifecycle, making it easy to unit test.

### Timing Behavior

Handle:

- Zero or invalid frame durations.
- Very large delta times.
- Reverse playback.
- Exact frame boundaries.
- Empty sequences.
- Single-frame sequences.
- Ping-pong boundary frames.
- Pause/resume.
- Playback speed changes.

Define precise behavior for each case.

---

## 9. Codex Authoring Tools

Because Codex is the primary sprite author, provide a convenient machine-readable workflow.

Do not require Codex to operate the Unreal Editor UI just to create artwork.

Implement a lightweight tool, preferably Python, for:

- XPM validation.
- XPM inspection.
- Pixel-grid extraction.
- Palette inspection.
- Animation manifest validation.
- Frame comparison.
- PNG preview generation.
- Sprite-sheet export.
- Optional animation export.

Suggested CLI:

```text
ckpixel validate Sprite.xpm
ckpixel inspect Sprite.xpm
ckpixel grid Sprite.xpm
ckpixel render Sprite.xpm --output Sprite.png
ckpixel validate animations.json
ckpixel sheet animations.json --animation idle
ckpixel diff Idle/000.xpm Idle/001.xpm
```

These commands are examples, not a mandatory command-line syntax.

The CLI should reuse the same format rules as the Unreal importer.

Avoid divergent parsing behavior.

If directly sharing the C++ parser is practical, consider a small standalone build target. Otherwise, maintain shared conformance fixtures and tests for the C++ and Python implementations.

### Codex Authoring Documentation

Create a short, explicit specification telling Codex how to produce valid sprites.

Include rules for:

- Keeping consistent canvas sizes.
- Keeping character proportions stable.
- Maintaining palette consistency.
- Preserving anchor points.
- Avoiding accidental single-pixel changes.
- Creating in-between animation frames.
- Timing attacks, idle animations, movement, and recovery.
- Avoiding arbitrary canvas translations when animating.
- Ensuring that animation previews can be reproduced deterministically.

The purpose is to make Codex reliable at creating and revising pixel animations over many iterations.

---

## 10. Robustness and Security

Treat XPM and JSON as untrusted input.

Implement strict bounds checks.

Consider:

- Negative or zero dimensions.
- Extremely large dimensions.
- Integer overflow.
- Excessive palette sizes.
- Invalid characters-per-pixel values.
- Truncated rows.
- Invalid palette references.
- Malformed string literals.
- Invalid escape sequences.
- Unsupported color specifications.
- Invalid JSON.
- Missing source files.
- Duplicate or invalid animation names.
- Path traversal.
- Cyclic metadata references if applicable.
- Resource exhaustion.

Never execute or compile XPM text as C/C++.

XPM parsing must be data parsing only.

Provide actionable error messages with source filenames and line numbers where possible.

An invalid frame should not crash the editor.

---

## 11. Performance Considerations

Aim for responsive editor interaction and efficient runtime use.

Requirements:

- Avoid excessive allocations during playback.
- Avoid unnecessary copies of pixel grids.
- Cache generated frame thumbnails.
- Cache generated render textures where appropriate.
- Invalidate caches only when required.
- Avoid decoding XPM during normal gameplay.
- Avoid repeated CPU-to-GPU texture uploads where a texture atlas is suitable.
- Handle larger sprite collections without blocking the editor unnecessarily.
- Release transient GPU resources correctly.

Consider memory usage when multiple animations share palettes or identical frames.

Do not introduce premature complexity; profile where appropriate.

---

## 12. Tests

Add tests using the repository's existing test conventions.

### XPM Parser Tests

Test:

- Minimal valid sprite.
- Transparency.
- Multiple colors.
- Multiple characters per pixel.
- Escaped characters.
- Invalid palette references.
- Incorrect row lengths.
- Malformed headers.
- Oversized dimensions.
- Invalid color definitions.
- Missing data.
- Whitespace preservation.
- Round-trip integrity where writing is supported.

### Animation Tests

Test:

- Single-frame animation.
- Multiple frames.
- Variable frame durations.
- Looping.
- Ping-pong.
- One-shot playback.
- Reverse playback.
- Frame stepping.
- Large delta times.
- Frame boundary conditions.
- Pause/resume.
- Frame skipping.
- Missing frame files.
- Incorrect canvas sizes.

### Import Tests

Test:

- XPM import.
- Animation manifest import.
- Reimport after changing an XPM.
- Reimport after changing a manifest.
- Preservation of Unreal-side asset settings.
- Expected handling of invalid files.

### Rendering Tests

Where practical, use deterministic image outputs or golden-image comparisons.

Ensure nearest-neighbor rendering preserves exact source colors.

Ensure palette overrides do not mutate source data.

---

## 13. Example Content

Create a small collection of sample assets:

```text
Examples/
  SimpleSprite/
    Sprite.xpm

  Character/
    animations.json
    Idle/
      000.xpm
      001.xpm
      002.xpm
    Walk/
      000.xpm
      001.xpm
      002.xpm
      003.xpm
    Attack/
      000.xpm
      001.xpm
      002.xpm
```

Use a simple, visually recognizable character with consistent proportions.

Include at least:

- A static sprite.
- A looping idle animation.
- A looping walk animation.
- A one-shot attack animation.

Use these examples as importer and viewer test cases.

---

## 14. Editor Usability and Polish

The viewer should feel like an established Unreal Editor tool.

Follow the existing Ck styling where possible.

Include:

- Appropriate icons.
- Consistent Slate spacing.
- Clear toolbar commands.
- Keyboard shortcuts.
- Useful tooltips.
- Responsive interaction.
- Sensible defaults.
- Dark-theme compatibility.
- Persistent preferences.
- Clear errors and warnings.

Suggested keyboard controls:

| Key | Action |
|---|---|
| Space | Play / pause |
| Left | Previous frame |
| Right | Next frame |
| Home | First frame |
| End | Last frame |
| F | Fit to window |
| G | Toggle grid |
| O | Toggle onion skin |
| R | Restart playback |
| Mouse wheel | Zoom |
| Middle-mouse drag | Pan |

Respect Unreal Editor shortcut conflicts where applicable.

A user should be able to inspect a newly imported animation immediately, with minimal setup.

---

## 15. Documentation

Document:

1. Module architecture.
2. Dependency graph.
3. Supported XPM syntax.
4. Animation manifest schema.
5. Import and reimport workflow.
6. Runtime animation usage.
7. Viewer functionality and shortcuts.
8. Rendering modes and limitations.
9. CLI usage.
10. Automated testing.
11. Adding new animations.
12. Troubleshooting import errors.

Include examples suitable for a Codex coding agent.

---

## 16. Implementation Strategy

Do not attempt to construct the entire system as an unverified monolithic change.

Proceed in coherent, independently compilable stages.

### Phase 1 — Repository Investigation and Design

Inspect the existing Ck plugin architecture.

Select final module names and public interfaces.

Identify reusable infrastructure.

Record major architectural decisions.

### Phase 2 — Core Representation and Parser

Implement the XPM parser, palettes, pixel grids, manifest parser, and animation evaluator.

Add automated tests.

Verify standalone functionality before introducing complex editor UI.

### Phase 3 — Unreal Assets and Importing

Implement asset types, import factories, source dependencies, and reimport.

Verify that assets serialize, reload, and cook correctly.

### Phase 4 — Basic Viewer

Implement native Slate integration, image preview, zoom, pan, timeline, and playback.

Ensure imported assets open correctly.

### Phase 5 — Advanced Viewer

Implement onion skinning, palette inspection, overlays, comparison, diagnostics, and configurable rendering previews.

### Phase 6 — Runtime Rendering

Implement the rendering resources and gameplay-facing playback interface.

Test packaged builds as well as editor builds.

### Phase 7 — Codex Authoring Tools and Polish

Complete CLI tooling, sample content, tests, documentation, and usability improvements.

At every stage:

- Compile relevant modules.
- Run available tests.
- Resolve warnings and include issues.
- Avoid introducing circular dependencies.
- Verify editor and runtime separation.
- Keep changes narrowly scoped.

Do not leave placeholder or fake implementations and describe them as complete.

If the full implementation cannot be completed in one session, leave a functional, tested subset and a precise record of unfinished requirements.

---

## 17. Acceptance Criteria

The implementation is successful when:

1. Codex can create an XPM file by writing a text-based pixel grid.
2. The file can be imported into Unreal Engine.
3. Double-clicking its asset opens a native pixel-art viewer.
4. The viewer accurately displays every source pixel.
5. An animation JSON file can reference multiple XPM frames.
6. The viewer plays animations using their correct frame durations.
7. The timeline supports inspection and scrubbing.
8. Zoom, pan, grid, transparency, and frame stepping work.
9. Onion skinning and frame comparison work.
10. The user can preview different rendering modes without changing source artwork.
11. Changes to XPM or JSON source files can be reimported.
12. Runtime code can select animations, advance playback, and resolve frames.
13. At least one runtime rendering path works in packaged builds.
14. Tests cover parsing, timing, and invalid inputs.
15. No circular dependencies are introduced.
16. The solution follows the existing Ck codebase conventions.
17. The viewer is hosted in `CkGameplayDebugger`, with minimal coupling to its eventual `CkTools` rename.

---

## 18. Final Constraints

**Do not build a pixel painting editor.**

**Do not create a proprietary pixel image format.**

**Do not introduce Pixelorama or Aseprite dependencies.**

**Do not flatten the authoritative source into PNG.**

**Do not make editor-only modules mandatory in packaged runtime builds.**

**Do not duplicate existing Ck infrastructure.**

**Do not assume Unreal APIs or module layouts without inspecting the actual installed engine and repository.**

The result should be a maintainable, modular, Codex-first pixel art pipeline that integrates naturally with the CkFoundation ecosystem.

Begin by examining the repository and identifying the appropriate module locations, dependencies, and reusable facilities. Then implement the system incrementally, compiling and testing as you proceed.