"""Initial-only preparation of four source-backed native BSDF masters, outside PIE.

Explicit UE Python entry point; never opens a map, starts PIE, quits, or launches an
editor. Host derivation must already have created AdvancedBsdfV1/Manifest.json.
All source, destination and reused-texture checks complete before asset writes.
Existing masters require ordinary .ush reload or separately reviewed regeneration.
"""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True
import unreal
from advanced_bsdf_settings import LOOKS, TEXTURE_PARAMETERS
from prepare_native_bsdf import _param

ROOT_ASSET = "/CkFoundation/CkUsf"
OWNER = "CkUsf.AdvancedBsdfPreparation.v1"
MANIFEST_TAG = "CkTests/Resources/CkUsf/AdvancedBsdfV1/Manifest.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Asset save failed: " + asset.get_path_name())


def _definition_path(look):
    return ROOT_ASSET + "/Looks/Native/DA_" + look


def _owned(path, asset_type):
    asset = unreal.load_asset(path)
    if not asset and unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError("Existing destination cannot be loaded: " + path)
    if asset and (not isinstance(asset, asset_type) or unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER) != "1"):
        raise RuntimeError("Existing destination ownership/class differs: " + path)
    return asset


def _settings(texture):
    return {name: texture.get_editor_property(name) for name in ["compression_settings", "srgb", "flip_green_channel",
        "address_x", "address_y", "mip_gen_settings", "power_of_two_mode"]}


def _expected(channel, resize):
    return {"compression_settings": (unreal.TextureCompressionSettings.TC_NORMALMAP if channel == "Normal" else
              unreal.TextureCompressionSettings.TC_DEFAULT if channel == "BaseColor" else unreal.TextureCompressionSettings.TC_MASKS),
            "srgb": channel == "BaseColor", "flip_green_channel": False,
            "address_x": unreal.TextureAddress.TA_WRAP, "address_y": unreal.TextureAddress.TA_WRAP,
            "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,
            "power_of_two_mode": (unreal.TexturePowerOfTwoSetting.RESIZE_TO_SPECIFIC_RESOLUTION if resize
                                  else unreal.TexturePowerOfTwoSetting.NONE)}


def _verify_texture(texture, channel, info):
    resize = info["runtime_resize_1024_square"]
    expected = _expected(channel, resize)
    if _settings(texture) != expected:
        raise RuntimeError("Texture sampler/color/normal/mip settings differ: " + texture.get_path_name())
    if resize and (texture.get_editor_property("resize_during_build_x") != 1024 or
                   texture.get_editor_property("resize_during_build_y") != 1024):
        raise RuntimeError("NPOT runtime resize differs: " + texture.get_path_name())
    size = (texture.blueprint_get_size_x(), texture.blueprint_get_size_y())
    first_size = size
    expected_size = (1024, 1024) if resize else (info["width"], info["height"])
    if size != expected_size:
        # Texture2D::GetSizeX/Y can expose a placeholder while platform data compiles.
        # The engine requires FinishCompilation before inspecting completed platform data.
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Editor.AsyncTextureCompilationFinishAll')
        size = (texture.blueprint_get_size_x(), texture.blueprint_get_size_y())
    if size != expected_size:
        raise RuntimeError("Texture runtime dimensions differ: " + texture.get_path_name() +
                           " / before=" + str(first_size) + " / finished=" + str(size) + " / expected=" + str(expected_size))
    return {"path": texture.get_path_name(), "source_sha256": info["source_sha256"],
            "runtime_source_sha256": info["sha256"], "source_dimensions": [info["width"], info["height"]],
            "runtime_dimensions": list(size), "runtime_resize_1024_square": resize,
            "pre_finish_dimensions": list(first_size), "finished_compilation_before_size_check": first_size != size,
            "source_aspect_ratio": info["width"] / info["height"], "runtime_aspect_ratio": size[0] / size[1],
            "settings": {key: str(value) if not isinstance(value, (bool, int, float)) else value
                         for key, value in expected.items()}, "normal_convention": info["normal_convention"]}


def _under(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise RuntimeError("Receipt path escaped its root: " + str(relative))
    return path


def prepare():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError("End PIE before advanced native BSDF preparation")
    if unreal.SystemLibrary.get_console_variable_int_value("r.Substrate") != 1 or \
            unreal.SystemLibrary.get_console_variable_int_value("r.Substrate.ProjectGBufferFormat") != 0:
        raise RuntimeError("Advanced native BSDFs require enabled Blendable Substrate")
    # Refuse both complete and partial previous setups, before any asset write.
    for look in LOOKS:
        if unreal.EditorAssetLibrary.does_asset_exist(ROOT_ASSET + "/GeneratedLooks/M_CkUsf_Look_" + look):
            raise RuntimeError("Native masters already exist; use ordinary CkUsf .ush reload, or explicit regeneration outside PIE. "
                               "Initial-only preparation refuses complete or partial existing setups: " + look)
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    sources = root / "Plugins/CkTests/Resources/CkUsf/AdvancedBsdfV1"
    manifest_path = sources / "Manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1 or set(manifest["materials"]) != set(LOOKS):
        raise RuntimeError("Unexpected advanced source manifest roster/schema")
    for key in ["generator", "decoder"]:
        if _sha(_under(root, manifest[key + "_source"])) != manifest[key + "_sha256"]:
            raise RuntimeError("Source derivation/decoder recipe changed")
    for item in manifest["provenance_evidence"]:
        if _sha(_under(sources, item["path"])) != item["sha256"]:
            raise RuntimeError("Copied license/metadata receipt changed")
    definition_class = unreal.load_class(None, "/Script/CkUsf.CkUsf_LookDefinition")
    generator_class = unreal.load_class(None, "/Script/CkUsfEditor.CkUsf_GeneratorSubsystem")
    if not definition_class or not generator_class:
        raise RuntimeError("Rebuild native BSDF CkUsf classes before preparation")
    definitions = {look: _owned(_definition_path(look), unreal.CkUsf_LookDefinition) for look in LOOKS}
    # Verify reflected fields/enums and generator entry point before any package is created.
    defaults = unreal.get_default_object(definition_class)
    defaults.get_editor_property("_SlabFuzz")
    for field, value in [("_SurfaceGraph", 3), ("_Domain", 0), ("_ShadingModel", 0), ("_BlendMode", 1)]:
        type(defaults.get_editor_property(field)).cast(value)
    generator = unreal.get_editor_subsystem(generator_class)
    if not callable(getattr(generator, "generate_look_material_for", None)):
        raise RuntimeError("Native generator Python API is unavailable")
    candidates = {}
    parameter_sets = {}
    for look, recipe in LOOKS.items():
        record = manifest["materials"][look]
        original_manifest_path = root / "Plugins/CkTests/Resources/CkUsf" / recipe["source_batch"] / "Manifest.json"
        if original_manifest_path.read_bytes() != _under(sources, record["source_manifest"]).read_bytes():
            raise RuntimeError("Original batch manifest differs from retained receipt: " + look)
        original = json.loads(original_manifest_path.read_text(encoding="utf-8"))["materials"][recipe["source_key"]]
        if record["license"] != "CC0-1.0" or record["asset_id"] != original["asset_id"]:
            raise RuntimeError("Source identity/license differs: " + look)
        shader = root / ("Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/" + look + ".ush")
        if not shader.is_file():
            raise RuntimeError("Missing authored native shader: " + look)
        bound = {}
        for parameter, channel in TEXTURE_PARAMETERS:
            info = record["maps"][channel]
            if info["source_sha256"] != original["maps"][channel]["sha256"]:
                raise RuntimeError("Original map pin differs: " + look + "/" + channel)
            if _sha(_under(root, info["source_path"])) != info["source_sha256"]:
                raise RuntimeError("Original source changed: " + look + "/" + channel)
            if channel == "Normal" and not str(info["normal_convention"]).startswith("DirectX"):
                raise RuntimeError("Explicit DirectX normal convention required")
            if info["derived"]:
                if channel != "BaseColor" or look not in ["NativeRubyVelvet", "NativeVarnishedWalnut"] or info["bit_depth"] != 8:
                    raise RuntimeError("Only reviewed BC8 derivatives may be imported")
                filename = _under(sources, info["path"])
                if _sha(filename) != info["sha256"]:
                    raise RuntimeError("Derived encoded BC8 changed")
                expected_path = ROOT_ASSET + "/Textures/Native/T_" + look + "_BaseColor"
                if info["runtime_asset"] != expected_path:
                    raise RuntimeError("Derived destination differs from owned namespace")
                texture = _owned(expected_path, unreal.Texture2D)
                if texture and (unreal.EditorAssetLibrary.get_metadata_tag(texture, "CkUsfAdvanced.SourceSHA256") != info["sha256"] or
                                unreal.EditorAssetLibrary.get_metadata_tag(texture, "CkUsfAdvanced.Manifest") != MANIFEST_TAG):
                    raise RuntimeError("Existing BC8 derivation ownership/hash differs")
            else:
                expected_path = ROOT_ASSET + "/Textures/Library/T_" + recipe["runtime_basename"] + "_" + channel
                if info["runtime_asset"] != expected_path:
                    raise RuntimeError("Reused destination differs from declared backing")
                filename = None
                texture = unreal.load_asset(expected_path)
                if not isinstance(texture, unreal.Texture2D):
                    raise RuntimeError("Verified backing texture missing: " + expected_path)
                if (unreal.EditorAssetLibrary.get_metadata_tag(texture, "CkUsfLibrary.SourceSHA256") != info["sha256"] or
                        unreal.EditorAssetLibrary.get_metadata_tag(texture, "CkUsfLibrary.Manifest") !=
                        "CkTests/Resources/CkUsf/" + recipe["source_batch"] + "/Manifest.json"):
                    raise RuntimeError("Backing texture ownership/source differs: " + expected_path)
            if texture:
                _verify_texture(texture, channel, info)
            bound[parameter] = [channel, info, filename, texture]
        candidates[look] = bound
        # Build descriptors now so reflected parameter APIs cannot fail after texture import.
        params = [_param(parameter, 2, bound[parameter][1]["runtime_asset"] + "." +
                         bound[parameter][1]["runtime_asset"].rsplit("/", 1)[1], index * 10)
                  for index, (parameter, channel) in enumerate(TEXTURE_PARAMETERS)]
        params += [_param(name, 1, value, index * 10) for index, (name, value) in enumerate(recipe["vectors"])]
        params += [_param(name, 0, value, index * 10) for index, (name, value) in enumerate(recipe["scalars"])]
        parameter_sets[look] = params
    # No asset mutation has occurred above this point.
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for bound in candidates.values():
        for parameter, entry in bound.items():
            channel, info, filename, texture = entry
            if texture:
                continue
            destination, name = info["runtime_asset"].rsplit("/", 1)
            task = unreal.AssetImportTask()
            task.filename = str(filename)
            task.destination_path = destination
            task.destination_name = name
            task.automated = True
            task.replace_existing = False
            task.save = False
            tools.import_asset_tasks([task])
            objects = task.get_objects()
            if len(objects) != 1 or not isinstance(objects[0], unreal.Texture2D) or objects[0].get_path_name() != info["runtime_asset"] + "." + name:
                raise RuntimeError("Unexpected BC8 import result")
            texture = objects[0]
            # Compression is fixed before sRGB: blue data must never trigger semantic auto-detection.
            for key, value in _expected(channel, info["runtime_resize_1024_square"]).items():
                texture.set_editor_property(key, value)
            if info["runtime_resize_1024_square"]:
                texture.set_editor_property("resize_during_build_x", 1024)
                texture.set_editor_property("resize_during_build_y", 1024)
            unreal.EditorAssetLibrary.set_metadata_tag(texture, OWNER, "1")
            unreal.EditorAssetLibrary.set_metadata_tag(texture, "CkUsfAdvanced.SourceSHA256", info["sha256"])
            unreal.EditorAssetLibrary.set_metadata_tag(texture, "CkUsfAdvanced.Manifest", MANIFEST_TAG)
            _save(texture)
            _verify_texture(texture, channel, info)
            entry[3] = texture
    report = {"manifest": MANIFEST_TAG, "manifest_sha256": _sha(manifest_path),
              "recipe_sha256": _sha(Path(__file__)),
              "settings_sha256": _sha(root / "Tools/UsfMaterials/advanced_bsdf_settings.py"),
              "param_helper_sha256": _sha(root / "Tools/UsfMaterials/prepare_native_bsdf.py"), "looks": {}}
    for look, recipe in LOOKS.items():
        definition = definitions[look]
        if not definition:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property("data_asset_class", definition_class)
            definition = tools.create_asset("DA_" + look, ROOT_ASSET + "/Looks/Native", definition_class, factory)
            if not definition:
                raise RuntimeError("LookDefinition creation failed: " + look)
            unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, "1")
        definition.set_editor_property("_LookName", look)
        definition.set_editor_property("_UshIncludePath", "/CkUsf/Looks/" + look + ".ush")
        definition.set_editor_property("_UshFunctionName", "CkUsf_Look_" + look)
        for field, value in [("_SurfaceGraph", recipe["surface_graph"]), ("_Domain", 0), ("_ShadingModel", 0), ("_BlendMode", 1)]:
            definition.set_editor_property(field, type(definition.get_editor_property(field)).cast(value))
        definition.set_editor_property("_SlabFuzz", recipe["slab_fuzz"])
        definition.set_editor_property("_DirectionalShading", False)
        definition.set_editor_property("_ToonProfile", None)
        definition.set_editor_property("_Parameters", parameter_sets[look])
        _save(definition)
        generator.generate_look_material_for(definition)
        material = unreal.load_asset(ROOT_ASSET + "/GeneratedLooks/M_CkUsf_Look_" + look)
        if not isinstance(material, unreal.Material):
            raise RuntimeError("Native master generation failed: " + look)
        if unreal.EditorAssetLibrary.get_metadata_tag(material, "CkUsf.SourceDefinition.v1") != definition.get_path_name():
            raise RuntimeError("Generated master source definition differs: " + look)
        errors = unreal.MaterialEditingLibrary.recompile_material(material)
        if errors:
            raise RuntimeError("Native shader errors: " + look + " / " + "; ".join(errors))
        for parameter, entry in candidates[look].items():
            if unreal.MaterialEditingLibrary.get_material_default_texture_parameter_value(material, parameter) != entry[3]:
                raise RuntimeError("Native texture binding differs: " + look + "/" + parameter)
        _save(material)
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        record = manifest["materials"][look]
        report["looks"][look] = {"definition": definition.get_path_name(), "master": material.get_path_name(),
            "surface_graph": recipe["surface_graph"], "slab_fuzz": recipe["slab_fuzz"],
            "source_identity": record["identity_notes"], "license": record["license"], "source_url": record["source_url"],
            "shader_sha256": _sha(root / ("Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/" + look + ".ush")),
            "textures": {parameter: _verify_texture(entry[3], entry[0], entry[1]) for parameter, entry in candidates[look].items()},
            "statistics": {field: getattr(stats, field) for field in ["num_pixel_shader_instructions", "num_vertex_shader_instructions", "num_samplers"]}}
    output = root / "Saved/UsfMaterialGallery/AdvancedBsdfPreparation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("USF_ADVANCED_BSDF_PREPARED " + str(output))
    return report


if __name__ == "__main__":
    prepare()
