"""Initial-only owned Adaptive hero preparation; no map travel, renderer changes or UI input."""
from pathlib import Path
import hashlib
import json
import unreal
from adaptive_bsdf_settings import LOOKS, SOURCE_RECEIPT
from prepare_native_bsdf import _param
from prepare_advanced_bsdf import _verify_texture, _expected

ROOT_ASSET = '/CkFoundation/CkUsf'
OWNER = 'CkUsf.AdaptiveBsdfPreparation.v1'
TAG = SOURCE_RECEIPT.removeprefix('Plugins/')


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _under(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise RuntimeError('Source escaped receipt root: ' + relative)
    return path


def _save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())


def refine():
    """Update only four reviewed silk scalar defaults on this recipe's owned assets."""
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world() or unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
        raise RuntimeError('Refinement requires the owned Adaptive editor outside PIE')
    name = 'AdaptiveSlubSilk'
    definition = unreal.load_asset(ROOT_ASSET + '/Looks/Adaptive/DA_' + name)
    material = unreal.load_asset(ROOT_ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
    if not isinstance(definition, unreal.CkUsf_LookDefinition) or not isinstance(material, unreal.Material):
        raise RuntimeError('Owned silk definition/master is missing')
    if (unreal.EditorAssetLibrary.get_metadata_tag(definition, OWNER) != '1' or
            unreal.EditorAssetLibrary.get_metadata_tag(material, 'CkUsf.SourceDefinition.v1') != definition.get_path_name()):
        raise RuntimeError('Silk refinement ownership differs')
    keys = ['UVScale', 'NormalStrength', 'LobeARoughnessScale', 'LobeARoughnessBias']
    targets = {key: value for key, value in LOOKS[name]['scalars'] if key in keys}
    params = list(definition.get_editor_property('_Parameters'))
    named = {str(param.get_editor_property('_Name')): param for param in params}
    if len(named) != len(params) or any(key not in named for key in keys):
        raise RuntimeError('Silk parameter roster differs')
    for key in keys:
        if int(named[key].get_editor_property('_Type').value) != 0:
            raise RuntimeError('Silk scalar type differs: ' + key)
    before = {key: named[key].get_editor_property('_DefaultScalar') for key in keys}
    for key, value in targets.items():
        named[key].set_editor_property('_DefaultScalar', value)
    definition.set_editor_property('_Parameters', params)
    _save(definition)
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    generator.generate_look_material_for(definition)
    material = unreal.load_asset(ROOT_ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
    if (not isinstance(material, unreal.Material) or
            unreal.EditorAssetLibrary.get_metadata_tag(material, 'CkUsf.SourceDefinition.v1') != definition.get_path_name()):
        raise RuntimeError('Refined silk master/source definition differs')
    errors = unreal.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError('Refined silk compile failed: ' + str(errors))
    for key, value in targets.items():
        actual = unreal.MaterialEditingLibrary.get_material_default_scalar_parameter_value(material, key)
        if abs(actual - value) > 1e-6:
            raise RuntimeError('Refined master default differs: ' + key)
    _save(material)
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    report = {'look': name, 'before': before, 'after': targets,
              'settings_sha256': _sha(root / 'Tools/UsfMaterials/adaptive_bsdf_settings.py'),
              'note': 'UVScale4 deliberately magnifies yarn detail about2.9x; source-scale reference is approximately11.5.'}
    (root / 'Saved/UsfMaterialGallery/AdaptiveBsdfRefinement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def prepare():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('End PIE before Adaptive preparation')
    if (unreal.SystemLibrary.get_console_variable_int_value('r.Substrate') != 1 or
            unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1):
        raise RuntimeError('Use the approved Adaptive startup profile')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    source = root / 'Plugins/CkTests/Resources/CkUsf/AdaptiveBsdfV1'
    receipt_path = root / SOURCE_RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt['schema_version'] != 1 or _sha(_under(root, receipt['generator_source'])) != receipt['generator_sha256']:
        raise RuntimeError('Adaptive receipt schema/generator differs')
    for evidence in receipt['evidence']:
        if _sha(_under(source, evidence['path'])) != evidence['sha256']:
            raise RuntimeError('Provenance evidence changed: ' + evidence['path'])
    for record in receipt['materials'].values():
        manifest_path = root / 'Plugins/CkTests/Resources/CkUsf' / record['source_batch'] / 'Manifest.json'
        if _sha(manifest_path) != record['manifest_sha256'] or record['license'] != 'CC0-1.0':
            raise RuntimeError('Original source receipt/license changed')
    definition_class = unreal.CkUsf_LookDefinition
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    defaults = unreal.get_default_object(definition_class)
    type(defaults.get_editor_property('_SurfaceGraph')).cast(5)
    candidates = {}
    for name, recipe in LOOKS.items():
        master_path = ROOT_ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name
        definition_path = ROOT_ASSET + '/Looks/Adaptive/DA_' + name
        if unreal.EditorAssetLibrary.does_asset_exist(master_path) or unreal.EditorAssetLibrary.does_asset_exist(definition_path):
            raise RuntimeError('Initial-only setup refuses existing masters/definitions: ' + name)
        bindings = {}
        for parameter, source_key, channel in recipe['textures']:
            utility = source_key == 'utility'
            info = dict(receipt['utilities'][channel] if utility else receipt['materials'][source_key]['maps'][channel])
            filename = _under(source if utility else root, info['path'] if utility else info['source_path'])
            if _sha(filename) != info['sha256']:
                raise RuntimeError('Texture source changed: ' + str(filename))
            runtime_name = info.get('runtime_name') or 'T_LibrarySilk_' + channel
            path = ROOT_ASSET + ('/Textures/Adaptive/' if utility else '/Textures/Library/') + runtime_name
            texture = unreal.load_asset(path)
            if not texture and unreal.EditorAssetLibrary.does_asset_exist(path):
                raise RuntimeError('Existing texture cannot load: ' + path)
            if texture and not isinstance(texture, unreal.Texture2D):
                raise RuntimeError('Texture destination class differs: ' + path)
            normalized_channel = 'Normal' if channel in ['Normal', 'SlubNormal'] else channel
            info.update(source_sha256=info['sha256'], runtime_resize_1024_square=info['width'] != info['height'])
            if texture:
                owner_key = 'CkUsfAdaptive.SourceSHA256' if utility else 'CkUsfLibrary.SourceSHA256'
                if unreal.EditorAssetLibrary.get_metadata_tag(texture, owner_key) != info['sha256']:
                    raise RuntimeError('Texture ownership/source differs: ' + path)
                if utility:
                    if (unreal.EditorAssetLibrary.get_metadata_tag(texture, OWNER) != '1' or
                            unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfAdaptive.Receipt') != TAG):
                        raise RuntimeError('Utility texture ownership/receipt differs: ' + path)
                else:
                    expected_manifest = 'CkTests/Resources/CkUsf/' + receipt['materials'][source_key]['source_batch'] + '/Manifest.json'
                    if unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.Manifest') != expected_manifest:
                        raise RuntimeError('Library texture manifest differs: ' + path)
                _verify_texture(texture, normalized_channel, info)
            elif not utility:
                raise RuntimeError('Verified library backing is missing: ' + path)
            bindings[parameter] = dict(channel=normalized_channel, info=info, file=filename, path=path, texture=texture)
        params = [_param(parameter, 2, item['path'] + '.' + item['path'].rsplit('/', 1)[1], index * 10)
                  for index, (parameter, item) in enumerate(bindings.items())]
        params += [_param(key, 1, value, index * 10) for index, (key, value) in enumerate(recipe['vectors'])]
        params += [_param(key, 0, value, index * 10) for index, (key, value) in enumerate(recipe['scalars'])]
        candidates[name] = (bindings, params)
    # No asset writes above this point. Existing textures are verified, never modified.
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for bindings, _ in candidates.values():
        for binding in bindings.values():
            if binding['texture']:
                continue
            destination, name = binding['path'].rsplit('/', 1)
            task = unreal.AssetImportTask()
            task.filename = str(binding['file'])
            task.destination_path, task.destination_name = destination, name
            task.automated, task.replace_existing, task.save = True, False, False
            tools.import_asset_tasks([task])
            objects = task.get_objects()
            if (len(objects) != 1 or not isinstance(objects[0], unreal.Texture2D) or
                    objects[0].get_path_name() != binding['path'] + '.' + name):
                raise RuntimeError('Unexpected utility texture import result')
            texture = objects[0]
            info = binding['info']
            for key, value in _expected(binding['channel'], info['runtime_resize_1024_square']).items():
                texture.set_editor_property(key, value)
            if info['runtime_resize_1024_square']:
                texture.set_editor_property('resize_during_build_x', 1024)
                texture.set_editor_property('resize_during_build_y', 1024)
            unreal.EditorAssetLibrary.set_metadata_tag(texture, OWNER, '1')
            unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfAdaptive.SourceSHA256', info['sha256'])
            unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfAdaptive.Receipt', TAG)
            _save(texture)
            _verify_texture(texture, binding['channel'], info)
            binding['texture'] = texture
    report = {'receipt': TAG, 'receipt_sha256': _sha(receipt_path), 'looks': {}}
    for name, recipe in LOOKS.items():
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', definition_class)
        definition = tools.create_asset('DA_' + name, ROOT_ASSET + '/Looks/Adaptive', definition_class, factory)
        if not definition:
            raise RuntimeError('Could not create Adaptive look definition: ' + name)
        unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, '1')
        for key, value in [('_LookName', name), ('_UshIncludePath', '/CkUsf/Looks/' + name + '.ush'),
                           ('_UshFunctionName', 'CkUsf_Look_' + name), ('_DirectionalShading', recipe['directional_shading']),
                           ('_SlabFuzz', False), ('_Parameters', candidates[name][1])]:
            definition.set_editor_property(key, value)
        for key, value in [('_SurfaceGraph', recipe['surface_graph']), ('_Domain', 0), ('_ShadingModel', 0), ('_BlendMode', 1)]:
            definition.set_editor_property(key, type(definition.get_editor_property(key)).cast(value))
        _save(definition)
        generator.generate_look_material_for(definition)
        material = unreal.load_asset(ROOT_ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if not isinstance(material, unreal.Material):
            raise RuntimeError('Adaptive master generation failed: ' + name)
        errors = unreal.MaterialEditingLibrary.recompile_material(material)
        if errors:
            raise RuntimeError('Adaptive material compile failed: ' + str(errors))
        for parameter, binding in candidates[name][0].items():
            if unreal.MaterialEditingLibrary.get_material_default_texture_parameter_value(material, parameter) != binding['texture']:
                raise RuntimeError('Adaptive texture binding differs: ' + name + '/' + parameter)
        _save(material)
        report['looks'][name] = {'master': material.get_path_name(), 'definition': definition.get_path_name(),
            'textures': {parameter: _verify_texture(item['texture'], item['channel'], item['info']) for parameter, item in candidates[name][0].items()},
            'shader_sha256': _sha(root / ('Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/' + name + '.ush'))}
    output = root / 'Saved/UsfMaterialGallery/AdaptiveBsdfPreparation.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
