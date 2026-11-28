"""Validate and import the six recorded batch-six looks, then generate their masters outside PIE."""
from pathlib import Path
import hashlib
import json
import struct
import unreal


LOOKS = {
    'linen': 'LibraryLinen',
    'smooth_leather': 'LibrarySmoothLeather',
    'mosaic': 'LibraryMosaic',
    'pine': 'LibraryPine',
    'limestone': 'LibraryLimestone',
    'galvanized_steel': 'LibraryGalvanizedSteel',
}
MANIFEST_TAG = 'CkTests/Resources/CkUsf/Batch6Textures/Manifest.json'


def _compression(channel):
    if channel == 'Normal':
        return unreal.TextureCompressionSettings.TC_NORMALMAP
    if channel == 'BaseColor':
        return unreal.TextureCompressionSettings.TC_DEFAULT
    return unreal.TextureCompressionSettings.TC_MASKS


def _settings(texture):
    return {key: texture.get_editor_property(key) for key in [
        'srgb', 'compression_settings', 'address_x', 'address_y', 'mip_gen_settings',
        'flip_green_channel', 'power_of_two_mode', 'lod_group']}


def prepare():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('End PIE before preparing the sixth texture-backed batch')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    source = (root / 'Plugins/CkTests/Resources/CkUsf/Batch6Textures').resolve()
    manifest = json.loads((source / 'Manifest.json').read_text(encoding='utf-8'))
    records = manifest['materials']
    if set(records) != set(LOOKS):
        raise RuntimeError('Batch six must contain exactly its six approved material keys')
    destination = '/CkFoundation/CkUsf/Textures/Library'
    candidates = []
    # Complete the source and ownership preflight before importing or changing any asset.
    for key, look_id in LOOKS.items():
        record = records[key]
        if record['look_id'] != look_id:
            raise RuntimeError('Unexpected batch-six look ID: ' + key)
        channels = {'BaseColor', 'Normal', 'Roughness'}
        if key == 'mosaic':
            channels.add('TileMask')
        if not channels <= set(record['maps']):
            raise RuntimeError('Missing required material maps: ' + key)
        for channel in sorted(channels):
            info = record['maps'][channel]
            filename = (source / info['path']).resolve()
            if not filename.is_relative_to(source):
                raise RuntimeError('Texture source is outside the recorded source directory')
            data = filename.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != info['sha256']:
                raise RuntimeError('Source map hash differs: ' + str(filename))
            width, height = info['width'], info['height']
            if type(width) is not int or type(height) is not int or min(width, height) <= 0:
                raise RuntimeError('Invalid recorded map dimensions: ' + str(filename))
            if data[:8] == b'\x89PNG\r\n\x1a\n':
                if len(data) < 24 or data[12:16] != b'IHDR' or struct.unpack('>II', data[16:24]) != (width, height):
                    raise RuntimeError('PNG dimensions differ from the manifest: ' + str(filename))
            if channel == 'Normal' and not str(info.get('normal_convention', '')).startswith('DirectX'):
                raise RuntimeError('Importer requires recorded DirectX tangent normals: ' + str(filename))
            name = 'T_' + look_id + '_' + channel
            path = destination + '/' + name
            texture = unreal.load_asset(path)
            if not texture and unreal.EditorAssetLibrary.does_asset_exist(path):
                raise RuntimeError('Existing texture could not be loaded for ownership validation: ' + path)
            if texture:
                if not isinstance(texture, unreal.Texture2D):
                    raise RuntimeError('Existing destination is not a Texture2D: ' + path)
                if (unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256') != digest
                        or unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.Manifest') != MANIFEST_TAG):
                    raise RuntimeError('Existing texture ownership/hash differs: ' + path)
            candidates.append((filename, channel, name, path, texture, digest, width, height))

    prepared = []
    for filename, channel, name, path, texture, digest, width, height in candidates:
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
            if (len(objects) != 1 or not isinstance(objects[0], unreal.Texture2D)
                    or objects[0].get_path_name() != path + '.' + name):
                raise RuntimeError('Unexpected texture import: ' + str(filename))
            texture = objects[0]
        resize = bool(width & (width - 1) or height & (height - 1))
        settings = {
            # Blue diffuse textures can be auto-classified as normal maps on import.
            # Compression must change first: normal compression forcibly disables sRGB.
            'compression_settings': _compression(channel),
            'lod_group': (unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if channel == 'Normal'
                          else unreal.TextureGroup.TEXTUREGROUP_WORLD if channel == 'BaseColor'
                          else unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR),
            'srgb': channel == 'BaseColor',
            'address_x': unreal.TextureAddress.TA_WRAP,
            'address_y': unreal.TextureAddress.TA_WRAP,
            'mip_gen_settings': unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,
            'flip_green_channel': False,
            'power_of_two_mode': (unreal.TexturePowerOfTwoSetting.RESIZE_TO_SPECIFIC_RESOLUTION
                                 if resize else unreal.TexturePowerOfTwoSetting.NONE),
        }
        for key, value in settings.items():
            texture.set_editor_property(key, value)
        if resize:
            # Preserve source pixels. Match the prior batch's explicit 1024-square runtime policy;
            # rectangular NPOT sources change aspect during the build, recorded in the receipt below.
            texture.set_editor_property('resize_during_build_x', 1024)
            texture.set_editor_property('resize_during_build_y', 1024)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256', digest)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.Manifest', MANIFEST_TAG)
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture):
            raise RuntimeError('Failed saving texture: ' + path)
        saved = unreal.load_asset(path)
        if not saved or _settings(saved) != settings:
            raise RuntimeError('Saved texture settings differ: ' + path)
        expected_size = (1024, 1024) if resize else (width, height)
        actual_size = (saved.blueprint_get_size_x(), saved.blueprint_get_size_y())
        if actual_size != expected_size:
            raise RuntimeError('Imported runtime dimensions differ: ' + path)
        if resize and (saved.get_editor_property('resize_during_build_x') != 1024
                       or saved.get_editor_property('resize_during_build_y') != 1024):
            raise RuntimeError('Runtime resize settings differ: ' + path)
        prepared.append({'path': path, 'sha256': digest, 'srgb': settings['srgb'],
                         'compression': str(settings['compression_settings']),
                         'lod_group': str(settings['lod_group']),
                         'source_size': [width, height], 'runtime_size': list(actual_size),
                         'source_aspect_ratio': width / height,
                         'runtime_aspect_ratio': actual_size[0] / actual_size[1],
                         'runtime_aspect_changed': resize and width != height,
                         'runtime_resize_for_streaming': resize, 'settings_verified_after_save': True})

    statistics = {}
    for look_id in LOOKS.values():
        unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Ck_Usf_GenerateLooks ' + look_id)
        material = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + look_id)
        if not material:
            raise RuntimeError('Master was not generated: ' + look_id)
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        statistics[look_id] = {field: getattr(stats, field) for field in [
            'num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers', 'num_uv_scalars']}
    output = root / 'Saved/UsfMaterialGallery/Batch6Preparation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'textures': prepared, 'statistics': statistics}, indent=2), encoding='utf-8')
    unreal.log('USF_LIBRARY_BATCH6_PREPARED ' + str(output))


if __name__ == '__main__':
    prepare()
