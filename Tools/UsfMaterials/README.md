# Verify the USF material studio

Status: downloaded, imported and opened in the existing editor. Conversion 3
was visually checked upright on the Toon station. The user approved the open,
brighter presentation; the explicit live-edit checks below remain available.
No C++ changed in this slice.

1. Run `Open-Studio.ps1` from this directory. It launches the selected checkout
   through UnrealToolbox, or leaves its existing editor running.
2. Outside PIE, enter this in the editor's console:

   `py "D:/Repos/CkPlugins_3/Tools/UsfMaterials/open_studio_in_editor.py"`

   Setup downloads the upstream CC BY 4.0 USD shader ball, records an immutable
   source revision, attribution and hash, imports a two-slot mesh and generates
   the five new looks plus Toon. It then enters USF Materials and frames Toon.
   This performs an external download and writes only the documented shader-ball
   sources/import and these six generated look masters.
3. Verify these observations explicitly:
   - The model is upright, smooth, correctly framed, has useful beveled/concave
     detail and has no Unreal logo. No checkerboard/fallback material appears.
   - N/B visit all six studio materials. Ceramic, copper, lacquer, rubber, wax
     and Toon are distinct and convincingly lit. T returns to Toon; F reframes
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
