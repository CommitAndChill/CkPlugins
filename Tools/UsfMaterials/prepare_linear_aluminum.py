"""Import the versioned linear machining maps without replacing the original circular finish."""
from pathlib import Path
import hashlib
import json
import unreal


def prepare(generate=True):
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('End PIE before importing the aluminum finish')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    source = root / 'Plugins/CkTests/Resources/CkUsf/Batch1Textures'
    receipt_path = source / 'AluminumLinear_v2/Receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    destination = '/CkFoundation/CkUsf/Textures/Library'
    candidates = []
    for channel in ['Normal', 'Roughness', 'Direction']:
        info = receipt['maps'][channel]
        if channel == 'Normal' and not str(info.get('normal_convention', '')).startswith('DirectX'):
            raise RuntimeError('Expected recorded DirectX tangent normals')
        filename = (source / info['path']).resolve()
        if not filename.is_relative_to(source.resolve()):
            raise RuntimeError('Source path escapes the texture directory')
        digest = hashlib.sha256(filename.read_bytes()).hexdigest()
        if digest != info['sha256']:
            raise RuntimeError('Source hash differs: ' + str(filename))
        name = 'T_LibraryAluminumLinear_' + channel
        path = destination + '/' + name
        texture = unreal.load_asset(path)
        if texture and unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256') != digest:
            raise RuntimeError('Existing texture ownership/hash differs: ' + path)
        candidates.append((channel, filename, name, path, texture, digest))
    results = []
    for channel, filename, name, path, texture, digest in candidates:
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
                raise RuntimeError('Unexpected import: ' + path)
            texture = objects[0]
        texture.set_editor_property('srgb', False)
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP
                                    if channel == 'Normal' else unreal.TextureCompressionSettings.TC_MASKS)
        if channel == 'Normal':
            texture.set_editor_property('flip_green_channel', False)
        texture.set_editor_property('address_x', unreal.TextureAddress.TA_WRAP)
        texture.set_editor_property('address_y', unreal.TextureAddress.TA_WRAP)
        texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256', digest)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.Manifest',
            'CkTests/Resources/CkUsf/Batch1Textures/AluminumLinear_v2/Receipt.json')
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture):
            raise RuntimeError('Could not save ' + path)
        results.append({'path': path, 'sha256': digest})
    if generate:
        unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Ck_Usf_GenerateLooks LibraryAluminum')
    (root / 'Saved/UsfMaterialGallery/Aluminum-Preparation.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    prepare()
