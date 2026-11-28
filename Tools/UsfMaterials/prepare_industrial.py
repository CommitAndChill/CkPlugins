"""Import the owned linear palette and deliberately generate the IndustrialPaint master outside PIE."""
from pathlib import Path
import hashlib
import json
import struct
import unreal


def prepare():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('Stop PIE before importing the industrial palette')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    source = root / 'Plugins/CkTests/Resources/CkUsf/IndustrialPalette'
    receipt = json.loads((source / 'SourceReceipt.json').read_text())
    destination = '/CkFoundation/CkUsf/Textures/Industrial'
    inputs = [('IndustrialDetail_RGBA.png', 'T_IndustrialDetail'),
              ('IndustrialPlacement_RGBA.png', 'T_IndustrialPlacement')]
    candidates = []
    for filename, name in inputs:
        path = destination + '/' + name
        texture = unreal.load_asset(path)
        data = (source / filename).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if receipt['outputs'][filename]['sha256'] != digest:
            raise RuntimeError('Palette receipt hash differs: ' + filename)
        expected_size = 1024 if name == 'T_IndustrialDetail' else 256
        if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>IIBB', data[16:26]) != (expected_size, expected_size, 8, 6):
            raise RuntimeError('Palette must be the recorded RGBA8 image: ' + filename)
        if texture:
            previous = unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfIndustrial.SourceSHA256')
            if previous != digest:
                raise RuntimeError('Existing texture ownership/hash differs: ' + path)
        candidates.append((filename, name, path, texture, digest))
    prepared = []
    for filename, name, path, texture, digest in candidates:
        if not texture:
            task = unreal.AssetImportTask()
            task.filename = str(source / filename)
            task.destination_path = destination
            task.destination_name = name
            task.automated = True
            task.replace_existing = False
            task.save = False
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            imported = task.get_objects()
            if len(imported) != 1 or imported[0].get_path_name() != path + '.' + name:
                raise RuntimeError('Unexpected import result for ' + filename)
            texture = imported[0]
        texture.set_editor_property('srgb', False)
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property('compression_no_alpha', False)
        texture.set_editor_property('address_x', unreal.TextureAddress.TA_WRAP)
        texture.set_editor_property('address_y', unreal.TextureAddress.TA_WRAP)
        texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfIndustrial.SourceSHA256', digest)
        prepared.append((path, texture))
    for path, texture in prepared:
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture):
            raise RuntimeError('Failed saving ' + path)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Ck_Usf_GenerateLooks IndustrialPaint')
    material = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_IndustrialPaint')
    if not material:
        raise RuntimeError('IndustrialPaint master was not generated')
    stats = unreal.MaterialEditingLibrary.get_statistics(material)
    report = {name: str(getattr(stats, name)) for name in dir(stats) if not name.startswith('_') and not callable(getattr(stats, name))}
    output = root / 'Saved/UsfMaterialGallery/IndustrialPreparation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'material': material.get_path_name(), 'statistics': report}, indent=2))
    unreal.log('USF_INDUSTRIAL_PREPARED ' + str(output))


if __name__ == '__main__':
    prepare()
