"""Import only original hash-pinned amber resources and create additive owned assets."""
from pathlib import Path
import hashlib
import json
import struct
import unreal
from prepare_native_bsdf import _param
from amber_specimen_settings import ASSET, LOOKS, RESOURCE

OWNER = 'CkUsf.AmberSpecimen.v1'


def prepare():
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Prepare amber outside PIE in the owned editor')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
        raise RuntimeError('Amber requires the separate Adaptive profile')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    source = root / RESOURCE
    manifest_path = source / 'Manifest.json'
    manifest = json.loads(manifest_path.read_text())
    fingerprint = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    generator_path = (root / manifest['generator_source']).resolve()
    if not generator_path.is_relative_to((root / 'Tools/UsfMaterials').resolve()) or hashlib.sha256(generator_path.read_bytes()).hexdigest() != manifest['generator_sha256']:
        raise RuntimeError('Original amber authoring source differs')
    if set(manifest['meshes']) != set(LOOKS) or set(manifest['maps']) != {'AmberNormal', 'AmberRoughness', 'AmberThickness', 'AmberTint', 'BotanicalBaseColor', 'BotanicalNormal', 'BotanicalRoughness'}:
        raise RuntimeError('Amber requires exact five-role/seven-map roster')
    def existing(path, cls, pin):
        asset = unreal.load_asset(path)
        if unreal.EditorAssetLibrary.does_asset_exist(path) and (not isinstance(asset, cls) or unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER) != pin):
            raise RuntimeError('Preserve differently owned asset: ' + path)
        return asset
    entries = {}
    for kind in ['meshes', 'maps']:
        for key, info in manifest[kind].items():
            path = (source / info['path']).resolve()
            if not path.is_relative_to(source.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != info['sha256']:
                raise RuntimeError('Amber source path/hash differs: ' + key)
            if kind == 'maps':
                data = path.read_bytes()
                if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (info['width'], info['height']) or data[24] != info['bit_depth']:
                    raise RuntimeError('Amber PNG container/dimensions/depth differ')
            elif info['slot'] != key or info['degenerate_triangles'] != 0:
                raise RuntimeError('Amber mesh slot/triangle validation failed')
            name = 'T_AmberSpecimen_' + key if kind == 'maps' else 'SM_AmberSpecimen_' + key
            folder = ASSET + '/Textures/Optical/Amber' if kind == 'maps' else '/CkTests/CkUsf/Showcase/AmberSpecimen'
            cls = unreal.Texture2D if kind == 'maps' else unreal.StaticMesh
            destination = folder + '/' + name
            entries[key] = dict(file=path, info=info, kind=kind, folder=folder, name=name, path=destination,
                                asset=existing(destination, cls, info['sha256']))
    for recipe in LOOKS.values():
        name = recipe['name']
        existing(ASSET + '/Looks/Optical/DA_' + name, unreal.CkUsf_LookDefinition, fingerprint)
        master = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if master and unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != ASSET + '/Looks/Optical/DA_' + name + '.DA_' + name:
            raise RuntimeError('Preserve differently owned amber master')
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError('Amber asset save failed')
    for key, entry in entries.items():
        if entry['asset']:
            continue
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = str(entry['file']), entry['folder'], entry['name']
        task.automated, task.replace_existing, task.save = True, False, False
        if entry['kind'] == 'meshes':
            options = unreal.FbxImportUI()
            options.import_mesh, options.import_materials, options.import_textures = True, False, False
            data = options.static_mesh_import_data
            data.combine_meshes, data.auto_generate_collision = True, False
            data.convert_scene, data.convert_scene_unit = False, False
            data.set_editor_property('coordinate_system_policy', unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES)
            data.import_uniform_scale = 1
            data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            task.factory, task.options = unreal.FbxFactory(), options
        tools.import_asset_tasks([task])
        objects = task.get_objects()
        if len(objects) != 1 or objects[0].get_path_name() != entry['path'] + '.' + entry['name']:
            raise RuntimeError('Amber import returned an unexpected destination')
        asset = objects[0]
        if entry['kind'] == 'maps':
            normal = key.endswith('Normal')
            asset.set_editor_property('srgb', entry['info']['srgb'])
            asset.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP if normal else unreal.TextureCompressionSettings.TC_DEFAULT if key in ['BotanicalBaseColor', 'AmberTint'] else unreal.TextureCompressionSettings.TC_MASKS)
            asset.set_editor_property('flip_green_channel', False)
            asset.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
            asset.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
        else:
            if key not in [str(item.material_slot_name) for item in asset.static_materials]:
                raise RuntimeError('Amber named material slot missing')
            nanite = asset.get_editor_property('nanite_settings')
            nanite.set_editor_property('enabled', False)
            asset.set_editor_property('nanite_settings', nanite)
        unreal.EditorAssetLibrary.set_metadata_tag(asset, OWNER, entry['info']['sha256'])
        save(asset)
        entry['asset'] = asset
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    for role, recipe in LOOKS.items():
        name = recipe['name']
        definition = existing(ASSET + '/Looks/Optical/DA_' + name, unreal.CkUsf_LookDefinition, fingerprint)
        palette_changed = False
        if definition and role == 'Body':
            # Explicitly migrate only the observed first-lookdev palette. Preserve
            # any other authoring difference instead of overwriting user choices.
            parameters = list(definition.get_editor_property('_Parameters'))
            for parameter in parameters:
                if str(parameter.get_editor_property('_Name')) == 'TransmissionColor':
                    color = parameter.get_editor_property('_DefaultVector')
                    if all(abs(getattr(color, channel) - value) < 1e-5 for channel, value in zip('rgba', [.97, .78, .40, 1])):
                        parameter.set_editor_property('_DefaultVector', unreal.LinearColor(.97, .70, .32, 1))
                        palette_changed = True
            if palette_changed:
                definition.set_editor_property('_Parameters', parameters)
                save(definition)
        if not definition:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property('data_asset_class', unreal.CkUsf_LookDefinition)
            definition = tools.create_asset('DA_' + name, ASSET + '/Looks/Optical', unreal.CkUsf_LookDefinition, factory)
            if not definition:
                raise RuntimeError('Could not create amber definition')
            parameters = [_param(parameter, 2, entries[key]['asset'].get_path_name(), i * 10) for i, (parameter, key) in enumerate(recipe['textures'])]
            parameters += [_param(key, 1, value, i * 10) for i, (key, value) in enumerate(recipe['vectors'])]
            parameters += [_param(key, 0, value, i * 10) for i, (key, value) in enumerate(recipe['scalars'])]
            for key, value in [('_LookName', name), ('_UshIncludePath', '/CkUsf/Looks/' + recipe['source'] + '.ush'), ('_UshFunctionName', 'CkUsf_Look_' + recipe['source']), ('_Parameters', parameters)]:
                definition.set_editor_property(key, value)
            definition.set_editor_property('_TwoSided', role != 'Body')
            for key, value in [('_SurfaceGraph', recipe['graph']), ('_Domain', 0), ('_ShadingModel', 0), ('_BlendMode', 0)]:
                definition.set_editor_property(key, type(definition.get_editor_property(key)).cast(value))
            unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, fingerprint)
            save(definition)
        material = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if not material or palette_changed:
            generator.generate_look_material_for(definition)
            material = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if not isinstance(material, unreal.Material) or unreal.MaterialEditingLibrary.recompile_material(material):
            raise RuntimeError('Amber generation or compile failed')
        save(material)
    report = dict(manifest_sha256=fingerprint, meshes={role: entries[role]['path'] for role in LOOKS}, looks={role: recipe['name'] for role, recipe in LOOKS.items()})
    (root / 'Saved/UsfMaterialGallery/Amber-Preparation.json').write_text(json.dumps(report, indent=2))
    return report
