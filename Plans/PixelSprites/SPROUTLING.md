# Approved Sproutling example

The user approved the creature design and conditionally approved the eight-frame sheet once its subtle breathing movement was confirmed. Native transcription retains the design with a fixed ten-entry indexed palette on a 32 by 32 canvas. XPM/JSON remain authoritative.

Source: `Plugins/CkFoundation/Tools/CkPixel/Examples/Sproutling/sproutling.json`, with eight neighboring XPM files. Import path: `/Game/PixelSpriteExamples/Sproutling.Sproutling`. The root sample directory is already covered by the existing always-cook configuration.

The loop lasts 1,980 ms, with 450/220/220/90/110/220/220/450 ms frame holds. The upper torso rises by one native pixel and shoulders expand first; lower belly/feet stay fixed. Leaf tips sway by one pixel. The brief half/closed blink occupies frames four/five. Foot rows 28-31 and origin `[16,29]` are identical throughout. The last pose matches the first.

Executed evidence:

- Production Python loader/CLI validates all eight XPM/JSON frames and exports the PNG sheet. Native-source invariants verify seven distinct poses, stable foot rows and a settled loop seam.
- GIF inspection verifies eight encoded frames with the exact declared holds and 1,980 ms total. `Saved/PixelSpriteAcceptance/Sproutling/sproutling-idle.gif` is derived from the indexed source, not an authoritative flattened asset.
- SproutlingGate1 failed compilation before any editor starts: the new test incorrectly used `TArray::Mid`. The test now compares bounds-checked ground indices directly.
- SproutlingGate2 Editor build passes; 52/53 selected Pixel tests pass, zero skipped/contaminated. Native example import validates the eight poses/feet and saves `Content/PixelSpriteExamples/Sproutling.uasset` plus exporter sidecar. The rendered Sproutling viewer test passes with actual source/breath/blink selection and mounted frame-step input.
- One existing Character `AuthoredWindow` test crashed during initial factory import in that broader run. No cause was proved. A bounded read-only review found no justified speculative production fix; symbols were unavailable for the crash frames. The same test then passed alone (`SproutlingAuthoredIsolated1`, 1/1), and the final unchanged viewer group passed (`SproutlingViewerGroup1`, 3/3 including Character and Sproutling together). The crash is retained in the logs; it is not called preexisting, harmless or fixed.
- `Saved/PixelSpriteAcceptance/Sproutling/Viewer-Sproutling.png` was directly inspected: the native creature, eight source files, duration timeline, palette and transparent checkerboard are visible. The generated approval sheet is preserved beside it as `Approved-Eight-Frame-Concept.png`.

No unrelated failure work was resumed. Source freeze was observed throughout Toolbox runs. The new art, native asset, example coverage and viewer sample test are local/uncommitted; earlier PixelSprite dev delivery is unchanged. No new cook/package result is claimed for this asset specifically.

## Direct dev publication - 2026-10-12

The approved creature, viewer layouts/time track and world gym are included in the direct dev publication batch. Submodule tips verified on origin/dev: Foundation `562da71fd1c4`, GameplayDebugger `e05ddc4e85cc`, Tests `4f4f4bc355b7`. Incremental build and focused Ck.Pixel acceptance passed 58/58 with five rendered tests, 0 skipped/contaminated; rendered PixelSpriteGym passed in 24s with its documented map/game override. No rebase was needed because all three fetched submodule bases matched the opening tips. Unrelated instructions, build profiles, procedural animation work and staged tags are excluded.
