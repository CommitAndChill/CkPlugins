"""Import only receipt-verified owned lamp resources; never replace unrelated assets."""
from pathlib import Path
import hashlib
import json
import struct
import unreal
from prepare_native_bsdf import _param
from tail_lamp_settings import ASSET, LOOKS, RESOURCE

OWNER = 'CkUsf.OpticalTailLamp.v1'


def _save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Could not save lamp asset: ' + asset.get_path_name())


def _existing(path, cls, source_hash):
    asset = unreal.load_asset(path)
    if not asset and unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError('Destination exists but cannot load: ' + path)
    if asset and (not isinstance(asset, cls) or unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER) != source_hash):
        raise RuntimeError('Preserve asset with different ownership/source: ' + path)
    return asset


def prepare():
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Lamp preparation requires the owned editor outside PIE')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
        raise RuntimeError('Lamp preparation requires the opt-in Adaptive profile')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    source = root / RESOURCE
    manifest = json.loads((source / 'Manifest.json').read_text(encoding='utf-8'))
    manifest_hash = hashlib.sha256((source / 'Manifest.json').read_bytes()).hexdigest()
    mesh_keys = {'Lens', 'Reflector', 'Housing', 'LED', 'Gasket', 'Fastener', 'LEDPackage'}
    map_keys = {'LensNormal', 'LensRoughness', 'LensThickness', 'ReflectorNormal', 'ReflectorRoughness',
                'HousingBaseColor', 'HousingNormal', 'HousingRoughness'}
    if set(manifest['meshes']) != mesh_keys or set(manifest['maps']) != map_keys:
        raise RuntimeError('Lamp receipt requires the exact seven components and eight source maps')
    generator_file = (root / manifest['generator_source']).resolve()
    blend_file = (source / manifest['blend']['path']).resolve()
    if (not generator_file.is_relative_to((root / 'Tools/UsfMaterials').resolve())
            or not blend_file.is_relative_to(source.resolve())
            or hashlib.sha256(generator_file.read_bytes()).hexdigest() != manifest['generator_sha256']
            or hashlib.sha256(blend_file.read_bytes()).hexdigest() != manifest['blend']['sha256']):
        raise RuntimeError('Lamp generator/editable source provenance differs')
    for recipe in LOOKS.values():
        if any(key not in map_keys for _, key in recipe['textures']):
            raise RuntimeError('Lamp recipe references a missing source map')
    entries = {}
    for kind in ['meshes', 'maps']:
        for key, info in manifest[kind].items():
            path = (source / info['path']).resolve()
            if not path.is_relative_to(source.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != info['sha256']:
                raise RuntimeError('Source path/hash differs: ' + key)
            if kind == 'maps':
                data = path.read_bytes()
                if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (info['width'], info['height']):
                    raise RuntimeError('Texture dimensions/container differ: ' + key)
            name = ('T_TailLamp_' + key) if kind == 'maps' else path.stem
            destination = (ASSET + '/Textures/Optical/' if kind == 'maps' else '/CkTests/CkUsf/Showcase/TailLamp/') + name
            cls = unreal.Texture2D if kind == 'maps' else unreal.StaticMesh
            entries[key] = dict(kind=kind, info=info, file=path, path=destination,
                                asset=_existing(destination, cls, info['sha256']))
    for name in LOOKS:
        _existing(ASSET + '/Looks/Optical/DA_' + name, unreal.CkUsf_LookDefinition, manifest_hash)
        master = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if master and unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != ASSET + '/Looks/Optical/DA_' + name + '.DA_' + name:
            raise RuntimeError('Preserve unrelated generated master: ' + name)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for key, item in entries.items():
        if item['asset']:
            continue
        task = unreal.AssetImportTask()
        destination, name = item['path'].rsplit('/', 1)
        task.filename, task.destination_path, task.destination_name = str(item['file']), destination, name
        task.automated, task.replace_existing, task.save = True, False, False
        if item['kind'] == 'meshes':
            options = unreal.FbxImportUI()
            options.import_mesh, options.import_materials, options.import_textures = True, False, False
            mesh_data = options.static_mesh_import_data
            mesh_data.combine_meshes = True
            mesh_data.auto_generate_collision = False
            mesh_data.convert_scene, mesh_data.convert_scene_unit = False, False
            mesh_data.set_editor_property('coordinate_system_policy', unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES)
            mesh_data.import_uniform_scale = 1.0
            mesh_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            task.factory, task.options = unreal.FbxFactory(), options
        tools.import_asset_tasks([task])
        objects = task.get_objects()
        if len(objects) != 1 or objects[0].get_path_name() != item['path'] + '.' + name:
            raise RuntimeError('Import did not return exactly owned target: ' + key)
        asset = objects[0]
        if item['kind'] == 'maps':
            # The source receipt's channel describes the PNG layout (RGB/R),
            # while these exact recipe keys describe the material semantics.
            normal = key.endswith('Normal')
            color = key.endswith('BaseColor')
            asset.set_editor_property('srgb', color)
            asset.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP if normal else
                                      unreal.TextureCompressionSettings.TC_DEFAULT if color else unreal.TextureCompressionSettings.TC_MASKS)
            asset.set_editor_property('flip_green_channel', False)
            asset.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
            asset.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
        else:
            slots = [str(slot.material_slot_name) for slot in asset.static_materials]
            if item['info']['slot'] not in slots:
                raise RuntimeError('Named lamp slot missing: ' + key + str(slots))
            nanite = asset.get_editor_property('nanite_settings')
            nanite.set_editor_property('enabled', False)
            asset.set_editor_property('nanite_settings', nanite)
        unreal.EditorAssetLibrary.set_metadata_tag(asset, OWNER, item['info']['sha256'])
        _save(asset)
        item['asset'] = asset
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    report = dict(manifest_sha256=manifest_hash, meshes={key: item['path'] for key, item in entries.items() if item['kind'] == 'meshes'}, looks={})
    for name, recipe in LOOKS.items():
        path = ASSET + '/Looks/Optical/DA_' + name
        definition = _existing(path, unreal.CkUsf_LookDefinition, manifest_hash)
        master_path = ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name
        # Recover only the exact two known first-import defaults before any scene/MID
        # exists. Preserve any other authoring difference for explicit review.
        if definition:
            parameters = list(definition.get_editor_property('_Parameters'))
            changed = False
            for parameter in parameters:
                key = str(parameter.get_editor_property('_Name'))
                if name == 'OpticalTailLampReflector' and key == 'Metallic' and not unreal.EditorAssetLibrary.does_asset_exist(master_path):
                    parameter.set_editor_property('_Name', 'MetalnessLevel')
                    changed = True
                if name == 'OpticalTailLampLens' and key == 'NormalStrength' and abs(parameter.get_editor_property('_DefaultScalar') - .25) < 1e-6:
                    parameter.set_editor_property('_DefaultScalar', 1)
                    changed = True
                if name == 'OpticalTailLampLED' and key == 'EmissionStrength' and abs(parameter.get_editor_property('_DefaultScalar') - 5) < 1e-6:
                    parameter.set_editor_property('_DefaultScalar', 40)
                    changed = True
            if name == 'OpticalTailLampLens' and 'DistortionStrength' not in [str(parameter.get_editor_property('_Name')) for parameter in parameters]:
                parameters.append(_param('DistortionStrength', 0, .02, 110))
                changed = True
            if changed:
                definition.set_editor_property('_Parameters', parameters)
                _save(definition)
                generator.generate_look_material_for(definition)
        if not definition:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property('data_asset_class', unreal.CkUsf_LookDefinition)
            definition = tools.create_asset('DA_' + name, ASSET + '/Looks/Optical', unreal.CkUsf_LookDefinition, factory)
            if not definition:
                raise RuntimeError('Could not create lamp definition: ' + name)
            params = [_param(parameter, 2, entries[key]['asset'].get_path_name(), i * 10) for i, (parameter, key) in enumerate(recipe['textures'])]
            params += [_param(key, 1, value, i * 10) for i, (key, value) in enumerate(recipe['vectors'])]
            params += [_param(key, 0, value, i * 10) for i, (key, value) in enumerate(recipe['scalars'])]
            for key, value in [('_LookName', name), ('_UshIncludePath', '/CkUsf/Looks/' + recipe['source'] + '.ush'),
                               ('_UshFunctionName', 'CkUsf_Look_' + recipe['source']), ('_Parameters', params)]:
                definition.set_editor_property(key, value)
            for key, value in [('_SurfaceGraph', recipe['graph']), ('_Domain', 0), ('_ShadingModel', 0), ('_BlendMode', 0)]:
                definition.set_editor_property(key, type(definition.get_editor_property(key)).cast(value))
            unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, manifest_hash)
            _save(definition)
        material = unreal.load_asset(master_path)
        if not material:
            generator.generate_look_material_for(definition)
            material = unreal.load_asset(master_path)
        if not isinstance(material, unreal.Material):
            raise RuntimeError('Master generation failed: ' + name)
        errors = unreal.MaterialEditingLibrary.recompile_material(material)
        if errors:
            raise RuntimeError('Lamp shader compilation failed: ' + str(errors))
        _save(material)
        report['looks'][name] = material.get_path_name()
    output = root / 'Saved/UsfMaterialGallery/TailLamp-Preparation.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
