# Pixel Sprite in-world gym

## Scope and contracts

The registered `Pixel Sprite` gym presents Sproutling through three stations: a point-sampled 2D shader, an edge-coverage AA 2D shader, and movable CkIsm boxes colored from the authored indexed frame. One player owns playback; pause, frame step, restart, and station framing are exposed in the gym controls.

The AA shader integrates alpha coverage while choosing one authored RGB color. It does not blend neighboring pixel colors. Its bounded 3x3 footprint targets magnified pixel art, not general minification filtering.

All 1024 box positions are reserved, including transparent cells that become visible later. A dedicated entity owner rolls back the complete visual setup on failure. Material bindings clear to transparent on invalidation. The settled-state probe verifies deferred ISM color data before runtime assertions; screenshots provide separate rendered acceptance.

Frames 2 and 6 move the left shoulder outline at row 13 from column 6 to column 7. Native acceptance reimports the source through the production importer and saves the corrected example asset.

## Verification

Python authoring tests: 28/28 passed in 13.424 seconds. Corrected manifest validates and the regenerated eight-frame sheet was visually inspected.

Native build passed. GymGate5 passed the 30 core PixelSprite tests; GymGate7 passed the renderer authoring fixture (valid shader maps and actual shader MID binding/clearing). The corrected Sproutling example was reimported and saved through the production importer.

GymRuntime2 passed the rendered in-world test in 32 seconds: one-clock advance, pause, frame step, restart, authored pixels, and settled CkIsm colors. Three screenshots were inspected. Its first launch revealed that the saved startup preference can redirect an explicit map URL; the test now selects the registered gym through the production switcher and restores LastGymName afterward.

Visual inspection found the creature overlapping station labels and a bright cube-material specular highlight. Display placement, framing, an oblique cube camera, and an ownership-checked zero-specular material upgrade are implemented and verified. GymGate8 built and passed the renderer fixture 1/1, with zero skipped/contaminated tests. Final GymRuntime4 passed in 23 seconds after the last script-only display lift; three fresh screenshots were inspected with station headings clear. The cube view retains ordinary diffuse world lighting.

Final captures: `Saved/PixelSpriteAcceptance/Gym/Aliased.png`, `EdgeAA.png`, and `PixelBoxes.png`. Open `/CkTests/TestGyms/TestGyms_CkTests_Level`, play, then use Tab to select `Pixel Sprite`. Keys 1/2/3 frame the stations; P pauses, N steps, R restarts. The same game-mode URL can be used through the Toolbox Gauntlet map override above.

Acceptance is scoped to this gym and the selected PixelSprite tests, not a full-suite or packaged-gym claim. The game log contains the startup FText serialization diagnostic outside this scope; the user explicitly deferred outside failures. No new commits or pushes were made. Unrelated staged tags and other existing work remain local.

Earlier fixture failures were traced to Unreal shortening mask pin `Input` to an empty name, and a redundant forced synchronous compile leaving no applied map. The fixture now uses normal authoring plus targeted resource completion, reads both materials' errors unconditionally, and still requires an applied shader map. No arbitrary delay or empty-errors-only success was introduced.

Launch map: `/CkTests/TestGyms/TestGyms_CkTests_Level?game=/Script/Angelscript.Ck_PixelSpriteGym_GameMode`.

## Direct dev publication - 2026-10-12

The approved creature, viewer layouts/time track and world gym are included in the direct dev publication batch. Submodule tips verified on origin/dev: Foundation `562da71fd1c4`, GameplayDebugger `e05ddc4e85cc`, Tests `4f4f4bc355b7`. Incremental build and focused Ck.Pixel acceptance passed 58/58 with five rendered tests, 0 skipped/contaminated; rendered PixelSpriteGym passed in 24s with its documented map/game override. No rebase was needed because all three fetched submodule bases matched the opening tips. Unrelated instructions, build profiles, procedural animation work and staged tags are excluded.
