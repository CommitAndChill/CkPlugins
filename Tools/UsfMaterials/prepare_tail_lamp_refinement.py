"""Add three owned finish variants; never rewrite original lamp assets."""
from pathlib import Path
import hashlib
import json
import unreal
from prepare_native_bsdf import _param
from tail_lamp_settings import ASSET, LOOKS

OWNER = 'CkUsf.OpticalTailLamp.Refined.v1'
REPLACEMENTS = {role: 'OpticalTailLampRefined' + role for role in ['Lens', 'Reflector', 'Housing']}


def prepare():
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Refinement preparation requires the owned editor outside PIE')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
        raise RuntimeError('Refinement preparation requires the opt-in Adaptive profile')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    source = root / 'Plugins/CkTests/Resources/CkUsf/TailLampRefinedV1'
    manifest = json.loads((source / 'Manifest.json').read_text())
    fingerprint = hashlib.sha256((source / 'Manifest.json').read_bytes()).hexdigest()
    if set(manifest['maps']) != {'LensNormal', 'LensRoughness', 'LensThickness'}:
        raise RuntimeError('Unexpected refinement map roster')
    generator_path = (root / manifest['generator']).resolve()
    if not generator_path.is_relative_to((root / 'Tools/UsfMaterials').resolve()) or hashlib.sha256(generator_path.read_bytes()).hexdigest() != manifest['generator_sha256']:
        raise RuntimeError('Refinement source generator differs')
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    def owned(path, cls, pin):
        asset = unreal.load_asset(path)
        if unreal.EditorAssetLibrary.does_asset_exist(path) and (not isinstance(asset, cls) or unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER) != pin):
            raise RuntimeError('Preserve differently owned asset: ' + path)
        return asset
    entries = {}
    # Validate every source and destination before starting imports or saves.
    for key, record in manifest['maps'].items():
        path = (source / record['file']).resolve()
        if not path.is_relative_to(source.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise RuntimeError('Refined source path/hash differs')
        destination = ASSET + '/Textures/Optical/Refined/T_TailLampRefined_' + key
        entries[key] = (path, destination, owned(destination, unreal.Texture2D, record['sha256']))
    for role, name in REPLACEMENTS.items():
        owned(ASSET + '/Looks/Optical/DA_' + name, unreal.CkUsf_LookDefinition, fingerprint)
        master = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if master and unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != ASSET + '/Looks/Optical/DA_' + name + '.DA_' + name:
            raise RuntimeError('Preserve differently owned master')
        for _, key in LOOKS['OpticalTailLamp' + role]['textures']:
            if role != 'Lens' and not unreal.load_asset(ASSET + '/Textures/Optical/T_TailLamp_' + key):
                raise RuntimeError('Original lamp backing missing')
    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError('Refinement save failed')
    textures = {}
    for key, (path, destination, asset) in entries.items():
        if not asset:
            folder, name = destination.rsplit('/', 1)
            task = unreal.AssetImportTask()
            task.filename, task.destination_path, task.destination_name = str(path), folder, name
            task.automated, task.replace_existing, task.save = True, False, False
            tools.import_asset_tasks([task])
            objects = task.get_objects()
            if len(objects) != 1 or objects[0].get_path_name() != destination + '.' + name:
                raise RuntimeError('Refinement imported an unexpected target')
            asset = objects[0]
            asset.set_editor_property('srgb', False)
            asset.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP if key.endswith('Normal') else unreal.TextureCompressionSettings.TC_MASKS)
            asset.set_editor_property('flip_green_channel', False)
            asset.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
            asset.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
            unreal.EditorAssetLibrary.set_metadata_tag(asset, OWNER, manifest['maps'][key]['sha256'])
            save(asset)
        textures[key] = asset
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    for role, name in REPLACEMENTS.items():
        destination = ASSET + '/Looks/Optical/DA_' + name
        definition = owned(destination, unreal.CkUsf_LookDefinition, fingerprint)
        recipe = LOOKS['OpticalTailLamp' + role]
        if not definition:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property('data_asset_class', unreal.CkUsf_LookDefinition)
            definition = tools.create_asset('DA_' + name, ASSET + '/Looks/Optical', unreal.CkUsf_LookDefinition, factory)
            if not definition:
                raise RuntimeError('Could not create refinement definition')
            parameters = []
            for index, (parameter, key) in enumerate(recipe['textures']):
                asset = textures[key] if role == 'Lens' else unreal.load_asset(ASSET + '/Textures/Optical/T_TailLamp_' + key)
                parameters.append(_param(parameter, 2, asset.get_path_name(), index * 10))
            parameters += [_param(key, 1, value, index * 10) for index, (key, value) in enumerate(recipe['vectors'])]
            overrides = {'RoughnessScale': .9, 'RoughnessBias': .07} if role == 'Reflector' else {'RoughnessScale': 1.2, 'RoughnessBias': .07} if role == 'Housing' else {'ThicknessVariation': .9}
            parameters += [_param(key, 0, overrides.get(key, value), index * 10) for index, (key, value) in enumerate(recipe['scalars'])]
            source_name = 'OpticalTailLampLensRefined' if role == 'Lens' else recipe['source']
            for key, value in [('_LookName', name), ('_UshIncludePath', '/CkUsf/Looks/' + source_name + '.ush'), ('_UshFunctionName', 'CkUsf_Look_' + source_name), ('_Parameters', parameters)]:
                definition.set_editor_property(key, value)
            for key, value in [('_SurfaceGraph', recipe['graph']), ('_Domain', 0), ('_ShadingModel', 0), ('_BlendMode', 0)]:
                definition.set_editor_property(key, type(definition.get_editor_property(key)).cast(value))
            unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, fingerprint)
            save(definition)
        master = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if not master:
            generator.generate_look_material_for(definition)
            master = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if not isinstance(master, unreal.Material) or unreal.MaterialEditingLibrary.recompile_material(master):
            raise RuntimeError('Refinement material generation/compile failed')
        save(master)
    report = dict(manifest_sha256=fingerprint, replacements=REPLACEMENTS)
    (root / 'Saved/UsfMaterialGallery/TailLamp-RefinedPreparation.json').write_text(json.dumps(report, indent=2))
    return report
