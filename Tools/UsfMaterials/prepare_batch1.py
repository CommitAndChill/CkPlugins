"""Import the recorded first-batch texture maps and generate only its six masters, outside PIE."""
from pathlib import Path
import hashlib
import json
import unreal


def prepare():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('End PIE before preparing the texture-backed library')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    source = root / 'Plugins/CkTests/Resources/CkUsf/Batch1Textures'
    manifest = json.loads((source / 'Manifest.json').read_text(encoding='utf-8'))
    destination = '/CkFoundation/CkUsf/Textures/Library'
    required = {'BaseColor', 'Normal', 'Roughness'}
    candidates = []
    for key, record in manifest['materials'].items():
        channels = required | ({'Mask'} if key == 'tile' else set())
        if key == 'silk':
            channels |= {'Direction', 'Anisotropy'}
        if key == 'aluminum':
            channels |= {'Direction'}
        if not channels <= set(record['maps']):
            raise RuntimeError('Missing material maps: ' + key)
        for channel in sorted(channels):
            info = record['maps'][channel]
            filename = (source / info['path']).resolve()
            if not filename.is_relative_to(source.resolve()):
                raise RuntimeError('Texture source is outside the recorded source directory')
            digest = hashlib.sha256(filename.read_bytes()).hexdigest()
            if digest != info['sha256']:
                raise RuntimeError('Source map hash differs: ' + str(filename))
            if channel == 'Normal' and not str(info.get('normal_convention', '')).startswith('DirectX'):
                raise RuntimeError('Importer requires recorded DirectX tangent normals: ' + str(filename))
            name = 'T_' + record['look_id'] + '_' + channel
            path = destination + '/' + name
            texture = unreal.load_asset(path)
            if texture and unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256') != digest:
                raise RuntimeError('Existing texture ownership/hash differs: ' + path)
            candidates.append((filename, channel, name, path, texture, digest, info))
    prepared = []
    for filename, channel, name, path, texture, digest, info in candidates:
        if not texture:
            task = unreal.AssetImportTask()
            task.filename = str(filename)
            task.destination_path = destination
            task.destination_name = name
            task.automated = True
            task.replace_existing = False
            task.save = False
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objects = task.get_objects()
            if len(objects) != 1 or objects[0].get_path_name() != path + '.' + name:
                raise RuntimeError('Unexpected texture import: ' + str(filename))
            texture = objects[0]
        texture.set_editor_property('srgb', channel == 'BaseColor')
        compression = unreal.TextureCompressionSettings.TC_DEFAULT if channel == 'BaseColor' else unreal.TextureCompressionSettings.TC_MASKS
        if channel == 'Normal':
            compression = unreal.TextureCompressionSettings.TC_NORMALMAP
            if not str(info.get('normal_convention', '')).startswith('DirectX'):
                raise RuntimeError('Importer requires recorded DirectX tangent normals: ' + name)
            texture.set_editor_property('flip_green_channel', False)
        texture.set_editor_property('compression_settings', compression)
        texture.set_editor_property('address_x', unreal.TextureAddress.TA_WRAP)
        texture.set_editor_property('address_y', unreal.TextureAddress.TA_WRAP)
        texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
        resize = info['width'] & (info['width'] - 1) or info['height'] & (info['height'] - 1)
        if resize:
            # Keep the original source pixels; only the runtime build is resampled for streaming/mips.
            texture.set_editor_property('power_of_two_mode', unreal.TexturePowerOfTwoSetting.RESIZE_TO_SPECIFIC_RESOLUTION)
            texture.set_editor_property('resize_during_build_x', 1024)
            texture.set_editor_property('resize_during_build_y', 1024)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256', digest)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.Manifest', 'CkTests/Resources/CkUsf/Batch1Textures/Manifest.json')
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture):
            raise RuntimeError('Failed saving texture: ' + path)
        expected_width, expected_height = (1024, 1024) if resize else (info['width'], info['height'])
        if texture.blueprint_get_size_x() != expected_width or texture.blueprint_get_size_y() != expected_height:
            raise RuntimeError('Imported dimensions differ: ' + path)
        prepared.append({'path': path, 'sha256': digest, 'srgb': channel == 'BaseColor',
                         'compression': str(compression), 'source_size': [info['width'], info['height']],
                         'runtime_size': [expected_width, expected_height], 'runtime_resize_for_streaming': bool(resize)})
    # The versioned linear finish supersedes only aluminum's original machining maps.
    from prepare_linear_aluminum import prepare as prepare_aluminum
    prepare_aluminum(generate=False)
    statistics = {}
    for record in manifest['materials'].values():
        name = record['look_id']
        unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Ck_Usf_GenerateLooks ' + name)
        material = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name)
        if not material:
            raise RuntimeError('Master was not generated: ' + name)
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        statistics[name] = {field: getattr(stats, field) for field in [
            'num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers', 'num_uv_scalars']}
    output = root / 'Saved/UsfMaterialGallery/Batch1Preparation.json'
    output.write_text(json.dumps({'textures': prepared, 'statistics': statistics}, indent=2))
    unreal.log('USF_LIBRARY_PREPARED ' + str(output))


if __name__ == '__main__':
    prepare()
