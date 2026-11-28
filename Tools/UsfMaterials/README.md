# Verify the USF material studio

## Retained Adaptive BSDF studies

The user-approved bounded Adaptive profile is separate from the normal Blendable gym.
`Launch-AdaptiveBsdf.ps1` launches an offscreen editor through Toolbox with process-only
Adaptive/closure-budget/TAA overrides. It does not rewrite project renderer configuration.
Use only this editor for `AdaptiveCandyPaint` and `AdaptiveSlubSilk`; existing native
Slab/Toon/ClearCoat studies remain on the normal Blendable profile.

After launch, `python Tools/UsfMaterials/adaptive_bsdf_command.py state` checks readiness,
then `scene` constructs a transient studio using the approved logo-free shader ball and
the existing prepared assets. `prepare` is initial-only and refuses existing targets.
`verify_adaptive_bsdf.py` owns serial source probes, restores exact source bytes and
material/rig settings, captures isolated responses and24 light-orbit phases per look.
Run `canonical_capture_png.py` to create audited display copies without changing PNG image
data or the original proof. This excludes UE5.8 exporter allocation bytes beyond IEND;
future session exports also validate that terminator. Preserve an existing proof/capture
set before repeating the fixed filenames. `make_adaptive_bsdf_gallery.py` requires both
a successful restored proof and its canonical-copy receipt, and verifies capture
hashes before writing `Saved/UsfMaterialGallery/Adaptive-BSDF-Gallery.html` and orbit clips.
Submit `quit` before builds or profile changes. No desktop input is used.

Paint uses two retained Slabs for an absorbing dyed medium over a conductor. Silk uses
two independent anisotropic lobes with licensed satin backing and authored slub utilities.
The UV4 showcase deliberately enlarges silk detail about2.9x; source-scale reference on
this mesh is near11.5. Yarn detail remains subtle at full-ball distance. Neither material
claims a supplied reference graph, calibrated scan, native flake population or neural rendering.
See Foundation's `GATE_ADAPTIVE_BSDF.md` for scope, provenance, evidence and limitations.

## Native BSDF studies (UE5.8)

Current native galleries: Saved/UsfMaterialGallery/Native-BSDF-Gallery.html and
Advanced-BSDF-Gallery.html. The advanced batch contains ruby velour, varnished walnut,
resin carbon weave and clean copper, with native fuzz and Simple Clear Coat responses.
The current campaign PROGRESS.md and ADVANCED_BSDF.md record evidence and limits;
older batch-specific counts/instructions below are historical contracts.

`derive_advanced_bsdf_sources.py` preserves source maps and writes immutable BC8 derivatives
with provenance. In the offscreen bridge, `advanced_bsdf_prepare` is initial-only and refuses
existing masters. `advanced_bsdf_refine` explicitly regenerates only owned carbon/copper
numeric defaults outside PIE. Ordinary source edits use live reload instead of either command.
`verify_native_bsdf.py --advanced --prefix AdvancedBsdf --orbit-frames 12` checks source edits,
feature controls, identities and exact restoration; run bridge drivers serially. The gallery
generator requires its successful restored receipt. Existing captures should be preserved
before repeating a prefix. No desktop input is used.

Status: downloaded, imported and opened in the existing editor. Conversion 3
was visually checked upright on the Toon station. The user approved the open,
brighter presentation; the explicit live-edit checks below remain available.
Industrial expansion: one additional live-authored master and four aging presets.
No C++ changed in this slice. Artistic acceptance of the industrial family is pending.
The approved breadth-first expansion adds six texture-backed materials: crepe satin silk,
pebbled leather, glazed tile/grout, finished oak, circular-brushed aluminum and matte plastic.
This later batch includes an opt-in C++ anisotropy/tangent contract; rebuild before using it.
Its source, limits and evidence are recorded in Foundation's
`docs/campaigns/2026-10-18-UsfMaterialLibrary/BATCH1.md`.

1. Run `Open-Studio.ps1` from this directory. It launches the selected checkout
   through UnrealToolbox, or leaves its existing editor running.
2. Outside PIE, enter this in the editor's console:

   `py "D:/Repos/CkPlugins_3/Tools/UsfMaterials/open_studio_in_editor.py"`

   On first preparation, setup downloads the upstream CC BY 4.0 USD shader ball, records an immutable
   source revision, attribution and hash, imports a two-slot mesh and generates
   the five studio looks plus Toon. Already prepared assets are reused. If missing,
   it imports the original industrial data palette and generates IndustrialPaint.
   It then enters USF Materials and frames Toon.
3. Verify these observations explicitly:
   - The model is upright, smooth, correctly framed, has useful beveled/concave
     detail and has no Unreal logo. No checkerboard/fallback material appears.
   - N/B visit sixteen specimens. Ceramic, copper, lacquer, rubber, wax, six texture-backed library materials, four industrial
     paint aging presets and Toon use the same comparison lighting. T returns to Toon; F reframes
     the selected specimen. The neutral stand does not dissolve or deform.
   - The outline is initially off; O toggles it. Image demos face the viewer and
     read upright. Displacement retains a continuous sphere.
   - While Ceramic is visible, temporarily set its `O.BaseColor` assignment in
     `Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/StudioCeramic.ush` to
     `O.BaseColor = float3(0.1, 0.8, 0.2);`, save and confirm it turns green in
     the same PIE session. Restore the original assignment and save to recover.
   - L reloads loaded materials; G explicitly reloads shared lighting HLSL.
     Inspect the fresh log for AngelScript/HLSL errors and ensures.

Please report whether these checks pass and whether the material presentation is
an improvement. If setup stops, report its error before attempting cleanup.

The first download resolves current upstream main once and records that immutable
revision in the source receipt. Actual geometry/license inspection must approve
that revision before visual acceptance; this is not a pre-inspected bundled model.
Subsequent setup runs reuse the receipt and reimport only an owned older conversion.
Material slots are resolved by their Specimen/CoreBase names; importer ordering
does not matter. Conversion version 2 repairs originally unmapped UV triangles
for tangent generation, retaining the original valid charts and vertex normals.
Rerunning setup upgrades only a mesh whose import source matches this gallery's
recorded source. Conversion 3 also rotates glTF Y-up geometry and normals to Z-up,
with its front toward -X. KeepXYZAxes import avoids a second axis conversion.
Original OBJ versions are preserved; an existing on-disk UAsset is backed up
under Saved/UsfMaterialGallery/BeforeConversion3 before this upgrade.

The old 13-model comparison catalog is an optional diagnostic exec path. Normal
studio startup uses only .ush-backed materials. To experiment with the Toon
station's shading model, edit the existing `@ckusf shading_model` declaration.

## Industrial enamel

Factory teal, Workshop ochre, Coastal blue and Abandoned olive are overrides of
one IndustrialPaint master. `IndustrialSurface.ush` owns reusable paint, primer,
steel, rust, dust, region and micro-normal helpers; `Looks/IndustrialPaint.ush`
owns composition. All are watched transitive dependencies of the loaded master.
Steel/paint/rust selection is surface-region blending. Optional wetness uses the
existing ClearCoat response under Substrate conversion, not retained multiple slabs.

`SurfaceTiling` controls the 1024 detail map independently of `MaskTiling` and
`MaskOffset` on the 256 placement map. Source channel descriptions, original
procedural provenance, generator revision and SHA256 live in
`Plugins/CkTests/Resources/CkUsf/IndustrialPalette/SourceReceipt.json`.
Regenerate identically with `python Tools/UsfMaterials/generate_industrial_palette.py`;
use a new output directory when revising immutable sources. Import/regenerate
deliberately outside PIE with `prepare_industrial.py` through the editor Python console.

DebugView: 0 lit, 1 region ownership, 2 roughness, 3 metallic, 4 placement, 5 normals.
Wear is clustered UV damage; it is not a curvature bake. Microdetail uses UV finite
differences. Chips have no silhouette displacement or physical thickness, and the
coat shares the substrate normal. At extreme distance, thresholding averaged mask
mips does not preserve exact coverage. Judge close and gameplay views before use.

## Input-independent inspection

Finish AngelScript edits before attaching Python tools. Import `studio_session`
from this Tools directory and call `start()` once in the editor. Its local JSON
queue never sends mouse, keyboard or clipboard input. For example, from the host:

`python Tools/UsfMaterials/studio_command.py capture --preset 1 --name Workshop.png`

Supported commands: prepare, open, capture, state, cost, gc, end, quit. Capture
routes HighResShot through the PIE player/GameViewportClient, avoiding the first
active editor viewport ambiguity in AutomationLibrary.take_high_res_screenshot.
The session must be idle before refresh. Source/parameter schema changes need
deliberate regeneration. Do not edit AS while this validation session is in PIE.

`python Tools/UsfMaterials/verify_industrial_reload.py` performs serial entrypoint
and shared-helper edit/recovery against four existing MIDs, with exact-byte cleanup,
object equality, override checks and real screenshot comparisons. It requires the
open studio session, NumPy and Pillow; it writes only owned source edits temporarily
and evidence under Saved. Do not run another shader-source writer concurrently.

## Texture-backed first batch

`source_batch1_textures.py` acquires/verifies the six selected licensed sets, retaining
original files, hashes, authors, license snapshots, channel conventions and derivation recipes.
Its cached manifest is `Plugins/CkTests/Resources/CkUsf/Batch1Textures/Manifest.json`.
`source_linear_aluminum.py` verifies the versioned linear-finish override recorded in
`AluminumLinear_v2/Receipt.json`. It reuses CC0 Metal009 brushed-steel N/R as machining
data with independently authored aluminum reflectance; it is not a scanned aluminum set.
`prepare_batch1.py` imports the original 22 maps plus three versioned linear-finish maps and generates the six masters,
outside PIE. All six sample BC/DirectX normal/roughness in .ush; silk adds authored direction
and anisotropy, aluminum adds a constant coherent axial direction field, tile adds an aligned glaze mask.
Extra source height/AO maps remain available without implying they are sampled at runtime.

The existing manual setup script prepares missing library assets automatically. For fully
input-independent validation, `Launch-Batch1Studio.ps1` launches through UnrealToolbox with
process-local `UE-CmdLineArgs` requesting offscreen real-RHI rendering and the explicit
`start_studio_session.py` console command. No project startup hook or desktop input is used.
Do not launch a duplicate if preparation/capture times out; inspect the existing process/log.

Bridge commands include library_prepare, library_cost, library_proof_begin and a `--look`
selector. `capture_batch1.py` captures matched close/macro/gameplay views; `--preview`
temporarily enables TAA at 100% and restores the original renderer cvars in finally.
Baseline AA=0 images remain separate. Ordinary `--shot` captures preserve the actual viewport;
HighResShot uses explicit 1280x720 for the source proof. Both route through the PIE player.
`make_batch1_gallery.py` assembles the ungraded capture evidence into a local HTML gallery
and labeled contact sheet, without changing material colors.

`verify_batch1_reload.py` tests each .ush entrypoint and the transitive shared sampling helper
with six existing masters/MIDs, all bindings/overrides preserved and exact-byte recovery.
`verify_batch1_direction.py` uses the owned, ordinarily disabled point component because
current Substrate Rect direct lighting ignores anisotropy; it restores point/Rect intensities
and diagnostic material overrides. The studio presentation remains the original three Rect lights.
`Run-Batch1Gate.ps1 -Mode Build` and `-Mode Test` provide detached incremental build and
fresh serial real-RHI CkUsf verification with actual exit receipts. Follow build-test preflight.

Aluminum refinement: end PIE, run `studio_command.py aluminum_prepare`, then reopen the
gym. This imports only the three new owned finish assets and regenerates only aluminum.
`verify_linear_aluminum.py` proves source mutation/recovery in its existing master/MID.
`Run-Batch1Gate.ps1 -Mode Aluminum` runs the fresh offscreen real-RHI
`GeneratesUsableMasters` test. The initial manifest and circular-finish assets remain
historical; the versioned receipt and new AS texture bindings define the active finish.

## Second mixed batch

`source_batch2_textures.py` pins the actual CC0 sources, authors, channel conventions,
normal conversion and original downloads under CkTests `Resources/CkUsf/Batch2Textures`.
The cotton slot is fine poplin rather than heavy canvas. Glass uses authored normal
and a concentration mask as subtle roughness variation, independently of its clear
transmission. The source identities and finish reuse are explicit in Manifest.json.

`prepare_batch2.py` validates all hashes/ownership before import, prepares 17 maps and
generates only the six batch-two masters outside PIE. `studio_command.py batch2_prepare`
runs it in the offscreen studio. The ordinary manual setup also prepares missing masters.
`capture_batch2.py` records all six close/macro/gameplay views in native AA and temporary
TAA, restoring renderer settings. `make_batch2_gallery.py` creates the ungraded gallery.

Run capture/proof/control scripts strictly serially: the bridge has one request/result
slot. Wait for the previous host process to exit, not merely a progress line.
`verify_batch2_reload.py` uses native game-viewport Shot, with existing masters/MIDs and
all parameter/texture snapshots. `verify_batch2_controls.py` exercises normal strength,
UV rotation/scale, roughness and each surface's specialized response and restores values.
The HighResShot shared-helper recovery failure for glass remains recorded separately;
native capture success is not an engine-readiness fix.

`glass_pane_begin` / `glass_pane_end` create/remove an owned PIE-only comparison over
the existing tile MID, using the same live glass MID. Ordinary gym presentation is
unchanged. `Run-Batch2Gate.ps1` runs fresh offscreen real-RHI GeneratesUsableMasters
without rebuilding C++ or invoking global Toon reload.

## Third mixed batch

Velvet, walnut, granite, brass, frosted glass and carbon fiber use recorded CC0 sources in
`Batch3Textures/Manifest.json`; brass reflectance is authored over steel-source machining,
and glass reuses a clean matte finish rather than claiming an optical scan. Carbon excludes
the upstream all-metallic map. `source_batch3_textures.py` and `prepare_batch3.py` preserve
sources and enforce import ownership. `batch3_prepare` regenerates these six outside PIE.

`capture_batch3.py`, `verify_batch3_reload.py`, `verify_batch3_controls.py`, and
`verify_batch3_frost.py` run strictly serially against the offscreen studio. The source proof
changes texture-sampling UVs plus color math, then restores exact bytes in existing objects.
Brass's anisotropy control uses compatible point lighting, restoring the studio lights.
The frost proof compares native/TAA panes, radius-zero/bypass, and transitive helper edits.
It reports numeric detail suppression and restoration, not user artistic approval.

The bounded surface SceneColor flags require the incremental C++ build via
`Run-Batch3Build.ps1`. `Run-Batch3Gate.ps1` selects the focused CkUsf module with real RHI,
covering the extension and compatible existing authoring/reload/generation behavior.
`make_batch3_gallery.py` presents ungraded captures and the required final pane descriptor;
`verify_batch3_evidence.py` reconciles source hashes, protected assets and actual gate exit.
All generated evidence lives in `Saved/UsfMaterialGallery`. Full claims and retained failed
candidates are recorded in Foundation's material-library campaign `BATCH3.md`.

## Fourth mixed batch

Knitted fabric, patent leather, porcelain-style glazed tile, terrazzo, translucent plastic
and cork use the recorded CC0 sources in `Batch4Textures/Manifest.json`.
`source_batch4_textures.py` retains source receipts and reproducible map transformations;
`prepare_batch4.py` imports nineteen runtime textures and generates six masters.
The porcelain-style finish uses a source-aligned tile/grout mask; its source does not
verify porcelain composition. Patent coating is authored over a leather source.
Plastic010 supplies a clean polymer surface finish, not measured volume optics.

Run `verify_batch4_fill.py`, `verify_batch4_specialty.py`, `capture_batch4.py`,
`verify_batch4_reload.py` and `verify_batch4_controls.py` strictly serially.
The source proof edits each entrypoint's texture sampling and color math (sourced roughness
for near-black patent leather), plus the shared helper, in the existing twenty-four library
masters/MIDs. Specialty inspections exercise
independent glaze/grout controls and plastic body/transmission coverage.
`surface_pane_begin` resolves grout on a flat inspection sample without changing the ball.

Only the new translucent-plastic station receives a local 80 cd Point fill. Its 300 cm
attenuation radius excludes the other library specimen bounds; neighbor renders and
point-to-studio restoration are recorded separately. Thin-surface plastic does not imply
volume scattering or blurred transmission. Diagnostic lighting uses runtime component
setters: editor property setters reconstruct AS actors and destroy their dynamic components.

`Run-Batch4Gate.ps1` runs the focused fresh real-RHI `GeneratesUsableMasters` gate without
a C++ rebuild. `verify_batch4_evidence.py` reconciles captures, exact source restorations,
protected prior hashes and the actual gate result. `make_batch4_gallery.py` links ungraded
captures and all source/technical evidence. See campaign `BATCH4.md` for execution results.

## Fifth mixed batch

Denim, smooth concrete, clean brick, satin stainless-style metal, plywood edge and cardboard
use the recorded CC0 sources in `Batch5Textures/Manifest.json`.
`source_batch5_textures.py` retains official sources and reproducible map/hash receipts;
`prepare_batch5.py` imports eighteen BC/DirectX-normal/roughness textures and generates six
masters. Brick preserves its native 1024x512 maps; UVAspect repeats V twice by default.
The steel source provides a very smooth microfinish, not a measured alloy or satin scan;
neutral conductor color and satin roughness are authored. Plywood depicts veneer edge layers.

Run `capture_batch5.py`, `verify_batch5_reload.py` and `verify_batch5_controls.py` serially
against the offscreen studio. The source proof changes sampling UVs and material color math
in the same thirty library masters/MIDs, then restores exact source bytes. Controls cover
normal strength, UV scale/rotation, roughness, cloth fuzz, pore/firing/fiber variation,
polish and optional plywood finish. No additional presentation lights or native extensions.

`Run-Batch5Gate.ps1` runs a fresh focused real-RHI `GeneratesUsableMasters` test without
rebuilding C++. `verify_batch5_evidence.py` checks actual test exit, recorded sources and
captures, bindings/restorations and protected earlier hashes. `make_batch5_gallery.py`
links original native/TAA views and source/technical evidence. See campaign `BATCH5.md`.

## Sixth mixed batch

Linen, smooth leather, glazed hexagonal mosaic, coated pine, limestone and galvanized steel
use the retained licensed sources in `Batch6Textures/Manifest.json`.
`source_batch6_textures.py` records provider licenses, exact source URLs/hashes, normal
conventions and transformations. `prepare_batch6.py` imports nineteen texture assets
(BC/N/R plus Mosaic TileMask) and generates only these six masters. Compression and semantic
LOD group are set before sRGB, overriding blue-diffuse false-positive normal detection; saved
settings remain strictly verified. Source dimensions
remain recorded; NPOT linen uses the existing explicit 1024-square runtime resize policy.

Mosaic reuses the supported glaze/grout response with its own source-aligned TileMask.
`verify_batch6_mosaic.py` checks glaze exclusion, independent grout color/roughness and
full restoration on a temporary flat sample using the existing live MID. Run it serially
with `capture_batch6.py`, `verify_batch6_reload.py` and `verify_batch6_controls.py`.
The source proof edits each look's texture sampling and color math plus the shared helper,
preserving all thirty-six library master/MIDs and bindings before exact byte recovery.

`Run-Batch6Gate.ps1` runs the fresh real-RHI focused generation gate without a C++ rebuild.
`verify_batch6_evidence.py` reconciles the actual exit/log, source/capture/asset hashes,
protected earlier files and required mosaic proof. `make_batch6_gallery.py` links original
renders and all source/technical records. Pine's source finish and any source-authored
variation stay documented; no new weathering overlay or presentation light is imposed.
See campaign `BATCH6.md` for results and limitations.


## Seventh mixed batch and bespoke woodland

Batch7 adds technical synthetic weave, slate, clean copper, glossy plastic, candle wax and
photo-derived glass-fiber cloth. `Manifest-v2.json` selects fine fiberglass; original sources
and candidates remain. Source identity and non-measured properties are explicit in BATCH7.md.
Use the serial capture/reload/control tools; the studio bridge has one request slot. Never overlap
driver commands. Source proof covers all42 library master/MID pairs. `Run-Batch7Gate.ps1` shares
one fresh real-RHI gate with the woodland look, without rebuilding C++.

The user's latest environment direction is bespoke, optionally non-repeating diorama textures.
`author_woodland_patch.py` creates the geometry-backed source in an isolated background Blender
CLI, then finalizes an approved existing scene and BC-only polish without rebuilding geometry.
Its selected manifest pins the actual authoring source, packed .blend, EXR masters, maps and
licensed source receipts. `source_woodland_leaves.py` reproduces the pinned leaf/soil sources.
Do not use the live Blender MCP or desktop input. V1/V2 are rejected art drafts, not shipped looks.

`generate_woodland_grid.py` validates the owned80cm grid; `prepare_woodland.py` strictly imports
only the selectedV3 source outside PIE and generates only EnvironmentWoodland. Allfive maps clamp.
After source-art inspection use `verify_woodland.py` serially: native/TAA views, source-map debug,
POM UV and vertex-depth controls, measured repeat noise, same-MID source/vertex changes and exact
recovery. The failed earlier generic environment endpoint experiment remains retained; no specific
renderer cause is established. Preserve all prior source maps, candidates and proof files.

## Reference river pebbles and selected-station inspection light

The user rejected WoodlandV3 visually. `source_pebble_reference.py` retains the CC0 Poly Haven
Ganges River Pebbles scan and provenance. `derive_pebble_runtime_color.py` exactly quantizes
encoded16-bit BaseColor to8-bit for this engine's sRGB import path; original maps remain intact.
`Manifest-runtime-v2.json` selects that representation. `prepare_river_pebbles.py` imports only
the new look's textures/master and reuses the protected80cm grid without resaving it.

EnvironmentRiverPebbles stays live-editable in `.ush`: texture sampling, UVs, color, roughness,
normal strength, bounded POM and actual vertex height. `verify_river_pebbles.py` runs32 captures
and4 reloads on the same two MID/master pairs. `verify_orbit_light.py` checks real ticking,
pause, retargeting, geometry, neighbor bounds and exact studio-rig recovery. Run bridge drivers
serially. `verify_orbit_lifecycle.py` separately exercises actual respawn and active EndPlay/GC.

I toggles one Point light around the selected station, P pauses, K resets; N/B retarget it.
The default studio lighting returns exactly when disabled. `encode_orbit_preview.py` packages
36 actual paused captures into a9second4fps preview at2x nominal speed, not real-time footage.
After the restored proofs, `Run-RiverPebblesGate.ps1` runs one fresh offscreen real-RHI gate.
`verify_river_pebbles_evidence.py` reconciles sources, assets, frames,389 protected files and gate;
`make_river_pebbles_gallery.py` creates the separate RiverPebbles gallery without altering old ones.

## Grass, dirt and mud diorama patches

The user explicitly authorized the existing tools as an exception to the missing canonical
CkTextureGeneration package in this checkout. `author_diorama_patches.py` runs in background
Blender CPU4, with no live Blender connection. SelectedV2 compositions retain packed sources,
licensed scan/photo inputs, calibrated32-bit EXR masters and aligned BC8/N16/R8/H16/AO8 maps.
The root manifest pins exact recipes, helper, source inputs and licenses. V1 art drafts remain.

`create_diorama_looks.py` creates three new `.ush`/AS definitions using the verified height-look
contract. `diorama_settings.py` keeps artistic presentation separate from source geometry range:
grass uses shallow1cm relief and vertex mip2 after full-height trials showed heightfield columns;
dirt/mud retain their source ranges. Grass is textured ground cover, not independent foliage.
`prepare_diorama_patches.py` validates all inputs/collisions before import, saves only15new
textures/3masters, verifies saved sizes/settings and reuses the protected grid without resaving.
Call `diorama_prepare` outside PIE after end/GC BEFORE opening the studio via the host bridge.

Six stations follow the existing river pair. Bridge keys are grass_pom/grass_displacement,
dirt_pom/dirt_displacement and mud_pom/mud_displacement; all prior selectors remain unchanged.
`verify_diorama_patches.py` runs serially with96native/TAA/debug/control/source-edit captures and
12reloads. It checks all8environment and42library identities and exact source/state recovery.
`verify_diorama_orbit.py` separately checks the moving light on all3newground looks. Never overlap
bridge drivers. End/GC/quit the owned editor, then run `Run-DioramaGate.ps1` for one fresh real-RHI
generation gate. `verify_diorama_evidence.py` reconciles actual sources, frames, controls, binaries
and396protected earlier files; `make_diorama_gallery.py` creates the separate local gallery.
# Native optical studios

## Amber inclusion specimen

`author_amber_specimen.py` creates/verifies original immutable AmberSpecimenV1 sources:
five named-role OBJ/MTL meshes and seven maps (amber normal/roughness/R16 optical path/
linear tint plus botanical sRGB base color/normal/roughness). Geometry supplies inclusion
silhouettes and depth; the optical cap does not pretend a flattened inclusion image is 3D.
Run `Launch-AmberSpecimen.ps1`, then `amber_specimen_command.py prepare` and `scene`.
Preparation imports only owned hash-pinned resources and creates five additive definitions
and masters. Existing lamp assets are preserved. Only the exact first-lookdev Body palette
is migrated to the selected honey palette; other authored values are preserved.

The existing native transmitting Slab supplies the cap; `AmberSpecimen.ush` samples all
amber maps and exposes independent edge/center thickness, reference distance, tint, IOR,
roughness, normal strength, UVs and PNO strength. `AmberInclusion.ush` supplies four opaque
two-sided consumers for leaflets, seed, stem and backing. This is a front-view staged
cabochon with an opaque rear support, not a fully traced closed solid or caustic solution.

`verify_amber_specimen.py` writes a separate unique-capture proof and refuses to overwrite
an existing report. It checks native readiness/identity, stable starting frames, optical
endpoints, cap/inclusion visibility, three source edits and exact recovery, prior-file
hashes and two motion sequences. `make_amber_gallery.py` checks proof/source/capture
hashes, PNG dimensions, native resources, local refs and full clip decoding before writing
`Saved/UsfMaterialGallery/Amber-Inclusions-Gallery.html`. Rendered image metrics describe
display-RGB response, not calibrated optical measurement. The inclusion shader assay is
an aggregate image check; it does not independently isolate all four opaque consumers.

## Tail-light workflows

Additive finish refinement preserves all original assets and proof. Run
`author_tail_lamp_refinement.py` to verify/create the immutable TailLampRefinedV1 maps.
After `Launch-TailLamp.ps1`, run `tail_lamp_command.py prepare_refined` before scene creation,
then `tail_lamp_command.py scene --refined`. This loads independent original/refined MIDs
over identical geometry; the floor stays fixed to the original material. The three new
definitions are OpticalTailLampRefinedLens/Reflector/Housing. Their numeric parameters
and texture sampling remain `.ush` editable through the shared lens/hardware functions.
`verify_tail_lamp_refinement.py` requires a fresh scene and writes a separate proof; it
refuses to replace an existing report. `make_tail_lamp_refined_gallery.py` checks the passed
proof, source/capture hashes, local references and full video decoding before presenting
`Saved/UsfMaterialGallery/Optical-TailLamp-Refined-Gallery.html`. Small pillow-cell detail
is intentionally subtle at the main view; the macro and motion views are the inspection aids.

First prototype evidence: `TailLamp-RenderedProof.json` and `TailLamp-GalleryInspection.json`
under Saved/UsfMaterialGallery. Fresh focused gates passed4/4 Adaptive and86/86 Blendable.
The proof records any strictly validated same-editor checkpoint reuse explicitly; captures
have run-unique filenames. Inspect the receipt before repeating or presenting a proof.
The bridge requests timed residency only for the eight lamp textures and submits missing
material permutations through public material statistics before querying completeness.
Native Pixel Normal Offset is screen-space distortion, not traced lens optics. User
artistic review remains pending; automated browser layout verification was policy-blocked.

`Launch-TailLamp.ps1` uses the same process-only Adaptive startup profile as the previous
hero pair, with `-RenderOffscreen`. It launches through UnrealToolbox and never uses desktop
input. `-BuildOnly` is incremental; `-Test` runs focused `OpticalTailLamp` real-RHI tests;
`-Test -Blendable` runs the CkUsf compatibility pattern. `-Build` combines with a test gate.
No persistent project renderer settings are changed.

Original reproducible source: `author_tail_lamp.py`,
`Plugins/CkTests/Resources/CkUsf/TailLampV1/Manifest.json` and packed editable `.blend`.
The seven meshes have centimeter bounds24x10x4.5 and eight original molded/finish maps.
Blender source previews are explicitly separate from actual Unreal captures.

After the owned studio is ready, use `tail_lamp_command.py prepare`, then `scene`, then
`capture --name <plain-PNG-name>` or `quit`. The Python `submit()` API supports bounded
numeric material overrides, camera/light-phase, exposure/light controls and a Refraction
show-flag diagnostic. Commands execute serially on the editor thread with a reentry guard.
Preparation verifies sources and destination ownership before importing; its two explicit
first-pass repairs rename the unfinished reflector parameter and refine owned lens/LED
defaults before any scene exists. It does not repair unrelated or unknown differences.

`verify_tail_lamp.py` records actual controls, native resource/object identity and live lens
entrypoint/shared-helper edits with exact source recovery. `make_tail_lamp_gallery.py`
consumes only a passing restored proof, verifies capture hashes and fully decodes its orbit
videos. Gallery target: `Saved/UsfMaterialGallery/Optical-TailLamp-Gallery.html`.

The lens uses native colored transmission + independent calibration/optical wall thickness.
Native Pixel Normal Offset uses1 as neutral strength, not IOR. It is a screen-space thin-sheet
approximation; no traced optical interfaces, caustics or photometric lamp accuracy are claimed.

