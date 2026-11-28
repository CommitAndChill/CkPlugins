"""One-time setup of two persistent native BSDF prototypes outside PIE; run explicitly in UE Python.

Existing CC0 Tiles133A maps are reused, never imported or modified. A single Slab
is a dielectric ceramic response, not a physical multilayer glaze. Native Toon
uses the engine's default stepped profile ramps and native lighting.
"""
from pathlib import Path
import hashlib
import json
import unreal

OWNER = "CkUsf.NativeBsdfPreparation.v1"
ROOT_ASSET = "/CkFoundation/CkUsf"
PROFILE_PATH = ROOT_ASSET + "/Profiles/TP_CkUsf_NativeCeramic"
LOOKS = {"NativePorcelainSlab": 1, "NativeCeramicToon": 2}
SCALARS = {"UVScale": 1.5, "UVRotation": 0.0, "NormalStrength": 0.12,
           "RoughnessScale": 0.6, "RoughnessBias": 0.04,
           "GroutNormalStrength": 0.7, "GroutRoughness": 0.88, "DebugView": 0.0}
VECTORS = {"TintColor": (1.0, 1.0, 1.0, 1.0), "GroutColor": (0.13, 0.14, 0.15, 1.0)}
CHANNELS = {"BaseColorMap": "BaseColor", "NormalMap": "Normal",
            "RoughnessMap": "Roughness", "TileMask": "TileMask"}


def _definition_path(look):
    return ROOT_ASSET + "/Looks/Native/DA_" + look


def _master_path(look):
    return ROOT_ASSET + "/GeneratedLooks/M_CkUsf_Look_" + look


def _owned(path, asset_class):
    asset = unreal.load_asset(path)
    if not asset and unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError("Existing destination cannot be loaded: " + path)
    if asset:
        if not isinstance(asset, asset_class):
            raise RuntimeError("Existing destination has the wrong class: " + path)
        if unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER) != "1":
            raise RuntimeError("Existing destination lacks this recipe's ownership: " + path)
    return asset


def _save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Asset save failed: " + asset.get_path_name())


def _param(name, kind, value, order):
    param = unreal.Ck_Usf_ParamDesc()
    param.set_editor_property("_Name", name)
    # ECk_Usf_ParamType: Scalar=0, Vector=1, Texture2D=2; cast avoids Python spelling aliases.
    param.set_editor_property("_Type", type(param.get_editor_property("_Type")).cast(kind))
    param.set_editor_property("_Group", "Textures" if kind == 2 else "Surface")
    param.set_editor_property("_SortPriority", order)
    field = {0: "_DefaultScalar", 1: "_DefaultVector", 2: "_DefaultTexturePath"}[kind]
    param.set_editor_property(field, unreal.LinearColor(*value) if kind == 1 else value)
    return param


def prepare():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError("End PIE before preparing native BSDF prototypes")
    if unreal.SystemLibrary.get_console_variable_int_value("r.Substrate") != 1:
        raise RuntimeError("Native BSDF prototypes require enabled Substrate")
    if unreal.SystemLibrary.get_console_variable_int_value("r.Substrate.ProjectGBufferFormat") != 0:
        raise RuntimeError("Native BSDF prototypes currently require Blendable GBuffer")
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    manifest_path = root / "Plugins/CkTests/Resources/CkUsf/Batch4Textures/Manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = manifest["materials"]["porcelain"]
    if source["asset_id"] != "Tiles133A" or source["license"] != "CC0-1.0":
        raise RuntimeError("Unexpected ceramic source identity/license")
    textures = {}
    for parameter, channel in CHANNELS.items():
        info = source["maps"][channel]
        filename = (manifest_path.parent / info["path"]).resolve()
        if not filename.is_relative_to(manifest_path.parent.resolve()):
            raise RuntimeError("Source map escaped the recorded source root")
        if hashlib.sha256(filename.read_bytes()).hexdigest() != info["sha256"]:
            raise RuntimeError("Source map hash changed: " + channel)
        path = ROOT_ASSET + "/Textures/Library/T_LibraryPorcelain_" + channel
        texture = unreal.load_asset(path)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError("Prepare verified batch-four textures first: " + path)
        if unreal.EditorAssetLibrary.get_metadata_tag(texture, "CkUsfLibrary.SourceSHA256") != info["sha256"]:
            raise RuntimeError("Existing ceramic texture has different source ownership: " + path)
        textures[parameter] = texture
    definition_class = unreal.load_class(None, "/Script/CkUsf.CkUsf_LookDefinition")
    generator_class = unreal.load_class(None, "/Script/CkUsfEditor.CkUsf_GeneratorSubsystem")
    if not definition_class or not generator_class:
        raise RuntimeError("Native CkUsf editor classes are unavailable")
    # Complete ownership and source checks before creating any package.
    profile = _owned(PROFILE_PATH, unreal.ToonProfile)
    definitions = {look: _owned(_definition_path(look), unreal.CkUsf_LookDefinition) for look in LOOKS}
    for look in LOOKS:
        master = unreal.load_asset(_master_path(look))
        if master:
            expected = _definition_path(look) + ".DA_" + look
            if not isinstance(master, unreal.Material) or unreal.EditorAssetLibrary.get_metadata_tag(master, "CkUsf.SourceDefinition.v1") != expected:
                raise RuntimeError("Existing master is owned by another definition: " + look)
        elif unreal.EditorAssetLibrary.does_asset_exist(_master_path(look)):
            raise RuntimeError("Existing master cannot be loaded: " + look)
        if master:
            raise RuntimeError("Native masters already exist; use ordinary CkUsf .ush reload, or explicit regeneration outside PIE. "
                               "This initial-only setup refuses complete or partial existing native masters: " + look)
        shader = root / ("Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/" + look + ".ush")
        if not shader.is_file():
            raise RuntimeError("Missing native shader source: " + str(shader))
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    if not profile:
        profile = tools.create_asset("TP_CkUsf_NativeCeramic", ROOT_ASSET + "/Profiles",
                                     unreal.ToonProfile, unreal.ToonProfileFactory())
        if not profile:
            raise RuntimeError("Native Toon profile factory failed")
        unreal.EditorAssetLibrary.set_metadata_tag(profile, OWNER, "1")
    # The resolver requires a saved profile; factory defaults contain native stepped ramps.
    _save(profile)
    params = [_param(name, 2, texture.get_path_name(), i * 10)
              for i, (name, texture) in enumerate(textures.items())]
    params += [_param(name, 1, value, i * 10) for i, (name, value) in enumerate(VECTORS.items())]
    params += [_param(name, 0, value, i * 10) for i, (name, value) in enumerate(SCALARS.items())]
    # Positional descriptor order must match the .ush signature: textures, vectors, scalars.
    for look, graph in LOOKS.items():
        definition = definitions[look]
        if not definition:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property("data_asset_class", definition_class)
            definition = tools.create_asset("DA_" + look, ROOT_ASSET + "/Looks/Native", definition_class, factory)
            if not definition:
                raise RuntimeError("LookDefinition creation failed: " + look)
            unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, "1")
        definition.set_editor_property("_UshIncludePath", "/CkUsf/Looks/" + look + ".ush")
        definition.set_editor_property("_UshFunctionName", "CkUsf_Look_" + look)
        definition.set_editor_property("_LookName", look)
        definition.set_editor_property("_SurfaceGraph", type(definition.get_editor_property("_SurfaceGraph")).cast(graph))
        definition.set_editor_property("_Domain", type(definition.get_editor_property("_Domain")).cast(0))
        definition.set_editor_property("_ShadingModel", type(definition.get_editor_property("_ShadingModel")).cast(0))
        definition.set_editor_property("_BlendMode", type(definition.get_editor_property("_BlendMode")).cast(1))
        definition.set_editor_property("_DirectionalShading", False)
        definition.set_editor_property("_ToonProfile", profile if graph == 2 else None)
        definition.set_editor_property("_Parameters", params)
        _save(definition)
        definitions[look] = definition
    generator = unreal.get_editor_subsystem(generator_class)
    report = {"source_manifest": str(manifest_path.relative_to(root)),
              "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "source_identity": source["identity_notes"], "license": source["license"],
              "profile": profile.get_path_name(), "profile_settings": "Native factory defaults on creation; existing owned profile edits retained",
              "looks": {}}
    for look, definition in definitions.items():
        generator.generate_look_material_for(definition)
        material = unreal.load_asset(_master_path(look))
        if not isinstance(material, unreal.Material):
            raise RuntimeError("Native master generation failed: " + look)
        errors = unreal.MaterialEditingLibrary.recompile_material(material)
        if errors:
            raise RuntimeError("Native shader compilation failed: " + look + " / " + "; ".join(errors))
        for parameter, texture in textures.items():
            if unreal.MaterialEditingLibrary.get_material_default_texture_parameter_value(material, parameter) != texture:
                raise RuntimeError("Generated native texture binding differs: " + look + "/" + parameter)
        _save(material)
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        shader = root / ("Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/" + look + ".ush")
        report["looks"][look] = {"definition": definition.get_path_name(), "master": material.get_path_name(),
            "shader_sha256": hashlib.sha256(shader.read_bytes()).hexdigest(),
            "textures": {name: texture.get_path_name() for name, texture in textures.items()},
            "statistics": {field: getattr(stats, field) for field in ["num_pixel_shader_instructions", "num_vertex_shader_instructions", "num_samplers"]}}
    output = root / "Saved/UsfMaterialGallery/NativeBsdfPreparation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("USF_NATIVE_BSDF_PREPARED " + str(output))
    return report


if __name__ == "__main__":
    prepare()
