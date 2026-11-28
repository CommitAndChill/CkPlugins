# Material Gym expansion: advanced materials, reusable layering, and live CkUsf authoring

## Current upgrade status — supersedes historical engine state below

Latest material slice: ADVANCED_BSDF.md and PROGRESS.md document four additional native
surfaces (ruby velour, varnished walnut, resin carbon weave, copper), opt-in native fuzz and
Simple Clear Coat. Incremental build and76/76 focused real-RHI tests pass; final rendered
source/control/restoration proof passes. Gallery: Saved/UsfMaterialGallery/Advanced-BSDF-Gallery.html.
The owned offscreen editor quit. New material work remains local; no user artistic approval
is inferred. Two obsolete texture-format advertisements were reconciled in backed-up local
generated metadata; all DLLs retained. This supersedes first-pair-only feature wording below.

The existing D:\Repos\UnrealEngineAngelscript checkout is UE5.8.4 from Hazelight's original
repository, with CK custom work reconciled and CommitAndChill origin/main-ck independently
verified at55c44c498c272fcc1f911d1c90e9885184b026f3 (2026-10-21). The approved exact lease
replaced7a4ad7f53ee2d472c778bc7748ca753f396a9108. Recovery refs and protected Iris work remain.
User approved focused bundled-dotnet testing:83/83 pass. Earlier upgrade Unreal gates103/103;
later native BSDF slice67/67 focused CkUsf real-RHI tests and incremental Build2 pass. These are
focused results, not a full-suite or packaged claim. Temporary serialized builds remain approved.

Read Plugins/CkFoundation/docs/campaigns/2026-10-18-UsfMaterialLibrary/ENGINE_UPGRADE.md and
PROGRESS.md for current evidence and limits. Two texture-backed native Slab/Toon sources,
persistent profiles/definitions/masters and gym stations now exist; offscreen rendered source
edit/recovery and lighting proofs passed for factory and refined three-level native Toon profiles.
Gallery: Saved/UsfMaterialGallery/Native-BSDF-Gallery.html. The owned offscreen editor quit.
See NATIVE_BSDF.md for evidence and limits; user artistic approval remains separate.
Native Toon ramps remain profile asset data; numeric material inputs and sampling are .ush editable.
Startup SDK validation under a shared hold remains a separate write-path review item.

Preserve substantial unrelated host/Foundation/Tests work. Engine publication does not authorize
publishing those repositories. Keep working offscreen without desktop input. The historical tables
below describe earlier baselines and must not override this status or current evidence.

## 1. One-line summary

Expand the existing USF Materials gym into a visually impressive, reusable game-material library, with mask-driven surface composition and appropriate Substrate shading, while preserving CkUsf's code-driven `.ush` authoring and live reload for every showcased material.

This is implementation work, not a research-only assignment. Build on the working gym and pipeline described below. Prioritize convincing materials and useful combinations over asset count or a speculative universal framework. Do not rebuild the gym from scratch.

## 2. Repository state and preserved work

Work in **D:\Repos\CkPlugins_3**, using its selected `CkPlugins.uproject`. The dependent engine is **D:\Repos\UnrealEngineAngelscript**, the project's UE 5.7 AngelScript fork, previously verified as 5.7.4. Recheck the association and installed version through the project tooling.

Published baseline, with local HEADs checked when this prompt was prepared:

| Repository | Local branch | Published target | HEAD |
| --- | --- | --- | --- |
| CkPlugins | `bugfix/selected-project-binaries` | `origin/dev` | `c66d212c04a828169735a84baf2468c08afaf4a4` |
| CkFoundation | `dev` | `origin/dev` | `a232a02886825cf8d6794d2d93871629ce401185` |
| CkTests | `dev` | `origin/dev` | `c33051d4cec4166a06d11ffe2063f0ff607e12b0` |
| Engine | `bugfix/selected-project-binaries` | `origin/main-ck` | `e628343442a5724ede61a61177fd4a073386110d` |

The root pointers already include the published Foundation and Tests fixes. Remotes are under **CommitAndChill**; verify sanitized fetch/push URLs without printing credentials. Branch names do not necessarily match published targets. Reinspect status, tracking, fetched history and ownership before Git operations. Do not change another checkout to update a local branch.

Foundation and Tests were clean. This continuation prompt is an intentionally local, uncommitted root file. Preserve unrelated engine dirt, particularly:

- `D:\Repos\UnrealEngineAngelscript\Engine\Source\Runtime\Engine\Private\Net\Experimental\Iris\DataStreamChannel.cpp` — unrelated user edit, **do not modify, stash, discard, stage or commit it**. Baseline SHA256: `69813456749AB1E6ACE335A81231761F589552ADBF5BDEB00949D7F2FE990C92`.
- Engine-local credential files, `BuildGraph/`, and `Engine/Saved_ParityEditor*/` directories are unrelated. Leave them alone; do not read or publish credentials.

Read the current project/framework instructions and applicable skills. Work in place: **no worktrees, clones, mirrors, repository copies, alternate checkouts, or artifact/cache deletion for a clean rebuild**. Preserve unrelated changes through explicit path/hunk staging. Do not introduce raw pointers without the user's explicit approval. Ask before Shipping; do not run local cook/package/staging jobs.

This task authorizes research, suitably licensed asset downloads, texture generation/import, supporting CkUsf/gym implementation, normal editor launches, incremental builds, tests, captures and iterative visual inspection. Continue through normal implementation phases without repeatedly asking permission. Escalate consequential renderer/architecture/scope decisions when required by repository instructions. Publication is a separate action: do not infer a new commit/push request from the previous task's completed delivery.

## 3. Active work and desired outcome

The user approved the current upright shader-ball presentation, removal of extra walls, and improved brightness. They now want a substantially richer material collection and reusable layering suitable for games.

Core requirements:

- **Every normally showcased material must remain editable live through `.ush`.** This is a standing expectation, including new coats, layered examples and shared helper libraries. A manually authored graph that bypasses that workflow is not an acceptable hidden exception.
- Reuse high-frequency tiling surfaces with independently scaled, potentially lower-resolution placement masks. Do not require a unique high-resolution final texture set for every mesh.
- Compose physically different responses: paint wear reveals steel; rust changes roughness and normals as well as color; coating damage exposes a distinct layer.
- Support artist controls for color, wear, rust, dirt, scratches, wetness, tiling, mask breakup and layer coverage where appropriate. Provide coherent presets and variations, not dozens of disconnected shaders.
- Distinguish **surface-region blending** from **physical layering**. Masked steel/paint/rust selection and varnish/water/clear-coat over a substrate are different operations. Use true Substrate composition where supported and worth its cost; label approximations honestly.
- Use actual rendered results at close-up and gameplay distances. Maintain useful reflections, plausible roughness and normal strength, and readable organization.

The material wishlist remains broad. Develop these families through shared components rather than separate bespoke implementations for every item:

| Family | Desired coverage |
| --- | --- |
| Metals | Brushed/anodized aluminum, polished/brushed stainless steel, galvanized steel, painted and weathered industrial steel, rust, oxidized copper, brass, titanium, chrome, machined/scratched metal, heat discoloration, perforated metal, diamond plate and oily metal. |
| Composites/manufactured | Plain/twill carbon fiber, forged carbon, fiberglass, Kevlar-style weave, matte/gloss/reinforced plastics, rubber/tire rubber, ceramic and powder coatings, clear-coated paint and automotive paint. Carbon fiber must distinguish weave, directional response and resin/coating. |
| Architectural | Polished/rough/weathered/cracked concrete, exposed aggregate, reinforced concrete, asphalt/damaged asphalt, granite, marble, limestone, sandstone, brick, tile and worn painted masonry. |
| Organic/natural | Raw/varnished/weathered/burnt wood, leather, fabric/canvas/synthetic weave, soil, sand, mud and moss-covered stone. |
| Advanced examples | Iridescent/pearlescent coatings, layered coats, wet stone, rain-covered paint, ice/frost, translucent plastic, frosted glass, subsurface wax and damaged multilayer coatings, when convincingly supported at reasonable cost. |

Build these reusable layered demonstrations, with visibly distinct presets for each:

1. **Industrial painted metal:** steel, primer, paint, exposed metal, chips, scratches, rust, dirt/dust and optional wetness. This is the first end-to-end hero example.
2. **Weathered concrete:** concrete, macro color, cracks, aggregate, stains, moss/dirt and erosion. Identify which detail comes from geometry, textures and masks.
3. **Carbon-fiber composite:** weave, orientation/directional highlights, resin/coat, micro-scratches and coating damage.
4. **Vehicle/mech armor:** reusable metal/primer/paint with markings, wear, oxidation, dirt and heat damage. Demonstrate dramatically different appearances from shared surfaces and masks.
5. **Environmental aging:** clean, light, heavy and abandoned presets on the same underlying system.

Do not treat every wishlist entry as requiring its own master or unique textures. Preserve the broad objective while sequencing quality-first vertical slices. Do not declare the whole expansion complete after one prototype.

## 4. Why the existing work is a foundation, not the finished expansion

Already implemented and accepted:

- Five `.ush` studio starters: **StudioCeramic, StudioCopper, StudioLacquer, StudioRubber, StudioWax**, plus the existing native **Toon** station. Existing procedural, image, WPO and other looks remain in the gym.
- A logo-free **USD Working Group shader ball**, not Unreal's branded preview ball and not a statue. It is **CC BY 4.0, not MIT**, with source attribution and an immutable receipt under the CkTests resources. Keep its existing legal provenance.
- Import conversion 3 corrects glTF Y-up to Z-up, with positions/normals transformed together and front toward -X; importer uses `KeepXYZAxes`. Conversion 2 repaired 6,912 originally collapsed-UV triangles without changing valid UV charts. Original sources/conversions are retained. Do not undo these repairs or assume this mesh already has ideal hand-painted mask/curvature UVs.
- Assign materials by **Specimen/CoreBase slot name**, never fixed index. Unreal imports CoreBase before Specimen. Keep the neutral core/base distinct from the specimen.
- Consistent local rect lights on lighting channel 1, positioned in world space after actor scaling: key 6000, fill 3600, rim 3000, attenuation radius 350. Fixed exposure is EV100 3.5, bloom 0.1. These are the accepted baseline, not untouchable artistic constants.
- **No extra backdrop walls.** Large black cards were added and removed at the user's request. Keep rows open and navigable. Do not reintroduce oversized walls or hide material weaknesses with darkness/glare.
- Image/raymarch demos use viewer-facing planes; WPO displacement keeps continuous sphere geometry. The global outline is opt-in, initially off.

The starters do not establish a rich texture library, painted masks, real anisotropic fiber response, general Substrate graph authoring or native multi-slab composition. Those are the new investigation/implementation frontier.

## 5. Available diagnostics and first evidence to collect

Inspect current source and the running gym before redesigning it. Record baseline captures under current settings, including a close-up and a wider view. Verify actual Substrate/GBuffer values before interpreting shading results.

Project defaults already contain:

```ini
[/Script/Engine.RendererSettings]
r.Substrate=True
r.Substrate.ProjectGBufferFormat=0
```

The verified baseline is desktop deferred **Substrate + Blendable GBuffer**, not Adaptive. No need to enable Substrate again or rebuild the existing Toon implementation.

Read these existing reports, interpreting older pending/blocked notes as history rather than overriding their later verification sections:

- `D:\Repos\CkPlugins_3\Plugins\CkFoundation\docs\campaigns\2026-10-18-CkUsfCustomShadingModels\SUBSTRATE_PROTOTYPE.md`
- `D:\Repos\CkPlugins_3\Plugins\CkFoundation\docs\campaigns\2026-10-18-UsfMaterialGallery\PROGRESS.md`
- `D:\Repos\CkPlugins_3\Plugins\CkFoundation\docs\campaigns\2026-10-18-UsfMaterialGallery\TEST_FAILURE_REPAIR.md`
- `D:\Repos\CkPlugins_3\Tools\UsfMaterials\README.md`

Latest completed gates: incremental editor build passed; **57/57 CkUsf tests** passed serially with real RHI, zero failed/skipped/contaminated and known-red exemptions disabled (2m23s). The new engine browser-policy regression passed **1/1** (29s). Logs are `D:\Repos\CkPlugins_3\Saved\Logs\UsfFailures-FinalSerial.log` and `D:\Repos\CkPlugins_3\Saved\Logs\UsfFailures-BrowserFresh.log`. These are a focused baseline, not repository-wide acceptance or proof of new layering.

Launch through `D:\Repos\CkPlugins_3\Tools\UsfMaterials\Open-Studio.ps1`. To prepare/open the gym from the editor console outside PIE:

```text
py "D:/Repos/CkPlugins_3/Tools/UsfMaterials/open_studio_in_editor.py"
```

The imported mesh and generated masters already ship. Inspect before rerunning import/generation unnecessarily. The bootstrap preserves temporary startup settings and frames Toon.

Gym controls: **N/B** next/previous of six studio materials and frame; **F** frame selected; **T/U** restore the Toon source material; **L** reload loaded look materials; **G** explicit shared-lighting reload; **O** toggle outline; **R** respawn looks. Keep existing working input/UI conventions. Read `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Source\CkSlateLayout\AUTHORING.md` before changing in-game UI.

## 6. Symptom-to-cause map

| Symptom or temptation | Established cause / correct response |
| --- | --- |
| Material edit seems to require restarting | Normal supported `.ush` edits already auto-reload loaded masters/MIDs. Trace generator/reload readiness, includes and metadata; do not replace the pipeline. |
| Shared Toon lighting does not update on ordinary material reload | Lighting is a global/material shader dependency. Use explicit `Ck_Usf_ReloadShadingModels`; preserve development-mode retries. |
| Source model disagrees with asset `_ShadingModel` | `// @ckusf shading_model ...` in the look entrypoint takes precedence. Use named declarations, not a numeric color/parameter trick. |
| Shader ball sideways / incorrect material slot | Preserve conversion 3 axes and name-based slot lookup in the setup script and showcase actors. |
| Refraction ensure during a later global reload | Previous wiring-only test fixtures leaked uncompiled materials into global iteration. Scope-bound retirement now fixes this; do not remove it or silence the ensure. |
| Editor dies in CEF during automation | Engine main-ck now separates browser creation policy from stable hardware capability, including inherited popups. Preserve that fix. |
| Generated Custom input/output collision | Reserved names are validated. DebugScene now uses `FillOpacity`, retaining `O.Opacity`; do not weaken validation. |
| Need arbitrary multi-slab or anisotropic authoring | Audit actual output structs, generator and renderer capabilities. Current Toon bridge does not establish those features. |
| Setup + tests exit before automation starts | Do not combine `-ExecutePythonScript` preparation with an automation run: it exits after the script. Prepare separately. Refresh discovery when adding new tests; zero matches is not a pass. |

## 7. Critical implementation files

| File | Role |
| --- | --- |
| `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Source\CkUsf\Shaders\CkUsf\Common.ush` | Surface/vertex input and numeric output contracts, existing reusable HLSL helpers. |
| `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Source\CkUsf\Public\CkUsf\LookDefinition\CkUsf_LookDefinition.h` | LookDefinition source paths, parameter descriptors, domain/settings and optional data channels. |
| `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Source\CkUsfEditor\Public\CkUsfEditor\Generator\CkUsf_Generator.cpp` | Code-driven material graph/master construction and reload preparation/application. |
| `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Source\CkUsfEditor\Public\CkUsfEditor\Generator\CkUsf_ShadingModelContract.cpp` | Source declarations, output wiring and supported renderer/model contracts. |
| `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Source\CkUsfEditor\Public\CkUsfEditor\Reload\CkUsf_ShaderReload.cpp` | Directory/dependency watching, loaded-material reload and explicit global commands. |
| `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Script\CkUsf\CkUsf_Studio_Assets.as` | Existing five studio LookDefinitions and ordered/grouped artist parameters. |
| `D:\Repos\CkPlugins_3\Plugins\CkTests\Script\CkUsf\CkUsfGym_PlayerController.as` | Station roster, material application, navigation, framing and controls. |
| `D:\Repos\CkPlugins_3\Plugins\CkTests\Script\CkUsf\CkUsfGym_Showcase.as` | Shared specimen loading, named-slot selection and source-material behavior. |
| `D:\Repos\CkPlugins_3\Plugins\CkTests\Script\CkUsf\CkUsfGym_StudioShowcase.as` | Lighting/exposure, standard specimens, image-plane and displacement variants. |
| `D:\Repos\CkPlugins_3\Tools\UsfMaterials\prepare_shader_ball.py` | Licensed source receipt, axis/UV conversion, owned import validation, backups and master preparation. |

Existing shaders are under `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Source\CkUsf\Shaders\CkUsf\Looks`. Shared Toon lighting is `D:\Repos\CkPlugins_3\Plugins\CkFoundation\Source\CkUsfRenderer\Shaders\ShadingModels\CkUsf_Toon.ush`. Mesh attribution/provenance is under `D:\Repos\CkPlugins_3\Plugins\CkTests\Resources\CkUsf\UsdShaderBall`.

## 8. Things ruled out / decisions to preserve

- Do not create a parallel hand-authored Material Editor library as the source of truth. Generated Unreal assets are expected; numerical material authoring and iteration stay in source.
- Do not replace the standard specimen with Unreal-logo geometry or a statue. Add suitable planes or beveled industrial pieces for surface/edge demonstrations, keeping one consistent comparison specimen.
- Do not assume Substrate makes custom Toon lighting or CkUsf integration unnecessary. Toon still relies on the engine bridge and shared plugin HLSL.
- Do not call parameter blending or the existing ClearCoat output an arbitrary native multi-slab stack. Explain what is actually evaluated.
- Do not infer asset rights from a software repository's MIT license. Verify each mesh/texture/HDRI's actual terms and redistribution/attribution requirements.
- Do not download a huge library, buy assets, or create dozens of tiny variations to inflate counts. Select a restrained reusable source palette with provenance.
- Do not claim performance from shader-count intuition, visual acceptance from compilation, or live reload from newly generated assets replacing the old scene.
- Do not reopen the six resolved test failures as outstanding bugs. Preserve the repaired tests and removed known-red entry.

## 9. Architecture notes, research and gotchas

### Existing CkUsf workflow

LookDefinitions (normally AngelScript assets) describe a `.ush` include/function, domain, parameters and supported material settings. The generator builds Unreal master assets; runtime usage creates MIDs. Existing `.ush` entrypoints return `FCkUsf_SurfaceOutput`; WPO uses a separate vertex-safe entrypoint. Surface input includes useful UV/world/normal/tangent data, with optional channels governed by metadata. Inspect the actual contract before inventing new fields or assuming vertex alpha, arbitrary textures, anisotropy or closures are exposed.

In particular, a VertexTangent input does not establish anisotropic shading support: the current `FCkUsf_SurfaceOutput` has no general Anisotropy output. Audit and implement the complete generator/output path if directional material response needs it.

Source selection supports declarations such as `// @ckusf shading_model Toon` or `ClearCoat`. Within the supported contract, changing the annotation and saving already updates the existing loaded material in the same editor. Model-specific settings/pins must be applied and obsolete ones removed atomically.

- `Ck.Usf.AutoReload 1`: automatic loaded-look reload on source saves, including tracked dependencies.
- `Ck_Usf_ReloadShaders`: manual loaded-look reload.
- `Ck_Usf_ReloadShadingModels`: explicit shared lighting/global dependency reload, enabling `r.ShaderDevelopmentMode` retries.
- `Ck_Usf_ReloadGlobalShaders`: narrower renderer-entrypoint command; it is not a substitute for reloading shared Toon lighting includes.
- `Ck_Usf_GenerateLooks <LookName>`: intentional asset generation/regeneration, not the normal save/reload loop.

Normal material edits must preserve existing master/MID identities and overrides. Changes to parameter layouts, graph topology or new engine/native code can require deliberate regeneration/builds; renderer-setting changes can require an initial restart. Do not promise instant topology changes through the current numeric HLSL contract. Global reload is explicit and potentially expensive; never put it on every save. Previous reload timings were single-run observations, not a performance guarantee.

### Substrate boundary to resolve before large architecture changes

The implemented Toon prototype is **opaque desktop deferred, Blendable GBuffer, legacy material-root inputs**, with a scoped native-engine bridge into Substrate direct lighting. It is **not a new layerable BSDF node**. Adaptive GBuffer, explicitly connected FrontMaterial graphs and arbitrary mixed Toon closures are not covered by its acceptance. Forward/mobile, Nanite/indirect stylization and path-traced Toon are also outside that proof.

Audit which new material features can use the existing output/generator path, which need a small code-generated Substrate graph extension, and which would need a different renderer configuration or deeper engine work. A Custom HLSL expression returning numeric surface properties does not by itself author arbitrary Substrate graph topology.

Research Slab BSDF, horizontal blend, vertical layer, coverage weight, parameter blending, anisotropy, coats, transmission and subsurface support in the actual engine fork. Distinguish engine capability from what CkUsf currently exposes. Do not silently switch the project to Adaptive or sacrifice existing Toon/live reload. If true multi-slab support requires that tradeoff, show a bounded source-grounded recommendation and consult the CTO. Continue useful supported material work while investigating; do not use an ambitious universal framework as a prerequisite for the first convincing example.

Use Astra for a bounded architecture/design review when the standing triggers apply, retaining lead ownership. Seek artistic input for the hero material rather than relying solely on technical abstractions.

### Reusable composition

Prefer a small family of reusable implementations with separate surface definitions, placement masks, blend helpers, physical composition and artist presets. Reuse existing CkUsf helpers before adding new modules. Support independent UV scales for detail and placement; consider world/triplanar projection, vertex RGB, packed masks, height-aware transitions, macro/micro variation and appropriate detail-normal blending. True curvature/cavity/edge wear needs a trustworthy source; orientation noise alone is not mesh curvature.

Shared helper edits must reload all affected loaded consumers. Preserve both stage legality and dependencies: derivatives/pixel-only inputs cannot leak into WPO/vertex compilation. Keep schema changes explicit, validation atomic and rejection non-mutating.

### Research references and sourcing

Research these for ideas, verifying claims against primary sources and this engine version. Do not assume identical implementations across games or confuse unrelated engines named Dawn:

- Paragon / Bradford Smith, GDC 2017: https://www.artstation.com/artwork/r98aEO
- Epic Substrate overview: https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-substrate-materials-in-unreal-engine
- Epic layered materials: https://dev.epicgames.com/documentation/en-us/unreal-engine/layering-materials-in-unreal-engine
- Epic layer authoring: https://dev.epicgames.com/documentation/en-us/unreal-engine/creating-layered-materials-in-unreal-engine
- Adobe dynamic material layering: https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/features/dynamic-material-layering
- Authoritative Crystal Dynamics Tomb Raider / Marvel's Avengers / Dawn-engine material presentations or production breakdowns, where available.

Evaluate existing project assets first, then sources such as Poly Haven (https://polyhaven.com/textures), ambientCG (https://ambientcg.com/), Fab (https://www.fab.com/) and Substance Community (https://substance3d.adobe.com/community-assets). A marketplace/community label does not establish a redistributable license. Record asset-specific source URL, license, attribution, revision/hash where available and modifications. Use legitimate downloads and procedural alternatives if sources are unsuitable. Keep immutable sources separate from imported assets.

Texture standards: correct sRGB/linear choices, Unreal normal convention, appropriate resolution/mips/filtering, explicit channel packing, independent mask/detail scales and distance-stable detail. Do not substitute excessive normal strength or metallic/roughness extremes for convincing surfaces.

Presentation standards: appropriate reflection/environment lighting, comparable exposure, useful close-up and gameplay views, open navigation, clean/weathered side-by-side examples and geometry suited to the feature. Preserve the approved brightness/open layout as the starting reference.

## 10. Concrete implementation and verification flow

1. Read this prompt, current AGENTS/development guidance and the reports above. Inspect status/engine association, existing source contracts and the actual gym. Preserve unrelated dirt and capture the baseline before changing presentation.
2. Produce a short capability map: supported today, small CkUsf extensions, and genuinely new Substrate/engine work. Research the listed workflows and select a small licensed texture palette. State a concrete first hero target and reusable component boundaries. Consult Astra before committing to an uncertain consequential approach.
3. Implement industrial painted metal end-to-end through the existing pipeline: reusable steel/paint/rust/dirt surfaces, independently scaled placement/detail data, believable exposed layers and a few visibly different presets. Add missing narrowly scoped generator support only where justified. Render and improve it before multiplying the library.
4. Prove live iteration immediately: in the same PIE/editor process, save a hero `.ush` edit and a shared blend-helper edit, confirm all affected existing instances update and retain overrides, restore exact source bytes and confirm recovery. Test explicit global reload only if shared lighting changed. Structural graph/schema changes must have a documented regeneration path.
5. Expand into the carbon-fiber, concrete, armor and aging demonstrations and the broader families. Show real differences in roughness, normals, reflectance and coating behavior. Use actual physical layering when supported; clearly distinguish parameter-blended alternatives. Do not settle for a single finished example as the whole requested library.
6. Improve organization, controls, framing and suitable comparison geometry while preserving source-material selection, optional outlines and open rows. Add close-up/gameplay-distance and clean/weathered comparisons. The user performs final artistic acceptance; explicitly ask them to inspect the opened gym when ready.
7. Measure or inspect texture samples, material statistics, closure usage where exposed, permutation count, draw implications and texture memory. Record actual settings/scenarios and measured versus inferred results. Compare cheaper variants where appropriate; do not invent timings or claim a benchmark from one capture.
8. Extend production-path tests only where they verify meaningful new contracts, invalid-input rejection, in-place reload, and material readiness. Keep generated test packages isolated from shipped content and retire incomplete fixtures. Check complete shader maps on game/render threads before pixel comparisons.
9. Build/test exclusively through `D:\Repos\CkPlugins_3\CkAuto\UnrealToolbox.exe`, with `--project=D:\Repos\CkPlugins_3`. Use the repository build-test skill, detached `Start-Process ... -PassThru -WindowStyle Hidden`, preserve the progress window, monitor the owned process/output, and never pass `--no-progress-window`. Never invoke raw UBT, Build.bat or automation editor commands. Reuse binaries for script/content-only changes. State the planned fresh-boot count before running and keep it proportional. Use a single lane for shader-source-mutating reload checks so concurrent editors cannot edit the same file. No duplicate gates; fresh final evidence after the final relevant code change.
10. Do not combine `-ExecutePythonScript` asset preparation with tests, and do not treat cached-list zero matches as green. Never suppress shader errors/ensures to pass a gate, automatically enable expensive global reload, reset DDC/artifacts, or undo the CEF/fixture fixes.
11. Deliver actual generated/imported assets, source and artist parameters, captures, provenance/license receipts, concise architecture/extension documentation and reproducible commands. Report the exact supported renderer modes, measured costs, reload mechanisms, tests run, remaining limitations and visual checks still needing the user. Finish the authorized implementation and iteration, not just a plan.

Acceptance requires a visibly expanded and improved library; reusable tiling surfaces plus independent masks; convincing layered demonstrations with meaningful variations and artist controls; appropriate, honestly described Substrate use; live `.ush` iteration for every new showcase; actual rendered inspection at useful distances; recorded cost/quality tradeoffs; and preserved existing gym/Toon behavior. Compilation alone is insufficient.

## 11. Suggested first message

“I’ll inspect the current CkUsf contracts and the approved gym first, then build a live-editable worn painted-metal hero as the first reusable layering slice. I’ll verify which physical Substrate features the current Blendable bridge can support before changing graph topology or renderer settings, and keep the existing Toon workflow and unrelated Iris edit intact.”
