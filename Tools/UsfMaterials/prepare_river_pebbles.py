"""Validate and import the selected dense river-pebble source, then generate its master outside PIE."""
from pathlib import Path
import hashlib
import json
import math
import struct
import unreal


LOOK_NAME = 'EnvironmentRiverPebbles'
MANIFEST_TAG = 'CkTests/Resources/CkUsf/PebbleReferenceV1/Manifest-runtime-v2.json'
ORIGINAL_TAG = 'CkTests/Resources/CkUsf/PebbleReferenceV1/Manifest.json'

def manifest_tag(channel):
    return MANIFEST_TAG if channel=='BaseColor' else ORIGINAL_TAG

CHANNELS = ['BaseColor', 'Normal', 'Roughness', 'Height', 'AO']


def preflight_grid(root):
    import importlib.util
    spec = importlib.util.spec_from_file_location('ck_usf_owned_river-pebble_grid', root / 'Tools/UsfMaterials/generate_woodland_grid.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    expected, canonical = generator.build()
    source = generator.DIRECTORY / canonical['obj_file']
    receipt = generator.DIRECTORY / (generator.SOURCE_NAME + '.json')
    mtl = generator.DIRECTORY / canonical['mtl_file']
    if hashlib.sha256(mtl.read_bytes()).hexdigest() != canonical['mtl_sha256']:
        raise RuntimeError('Ground material-library source differs')
    if source.read_bytes() != expected or json.loads(receipt.read_text(encoding='utf-8')) != canonical:
        raise RuntimeError('Ground grid source/receipt differs from the canonical generator')
    destination = '/CkTests/CkUsf/Showcase/' + generator.NAME
    mesh = unreal.load_asset(destination)
    if not mesh and unreal.EditorAssetLibrary.does_asset_exist(destination):
        raise RuntimeError('Existing ground asset cannot be loaded for ownership validation')
    if mesh:
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError('Existing river-pebble destination is not a StaticMesh; preserve it')
        import_data = mesh.get_editor_property('asset_import_data')
        if (not import_data
                or unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.SourceSHA256') != canonical['sha256']
                or unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.Generator') != canonical['generator']
                or Path(import_data.get_first_filename()).resolve() != source.resolve()):
            raise RuntimeError('Existing river-pebble mesh ownership/source differs; preserve it')
    return source, canonical, destination, mesh


def _compression(channel):
    if channel == 'Normal':
        return unreal.TextureCompressionSettings.TC_NORMALMAP
    if channel == 'BaseColor':
        return unreal.TextureCompressionSettings.TC_DEFAULT
    if channel == 'Height':
        return unreal.TextureCompressionSettings.TC_GRAYSCALE
    return unreal.TextureCompressionSettings.TC_MASKS


def _settings(texture):
    return {key: texture.get_editor_property(key) for key in [
        'srgb', 'compression_settings', 'address_x', 'address_y', 'mip_gen_settings',
        'flip_green_channel', 'power_of_two_mode', 'lod_group']}


def validate_manifest(manifest):
    record=manifest['materials']['pebbles']
    if manifest['schema_version']!=1 or record['look_id']!=LOOK_NAME or set(record['maps'])!=set(CHANNELS):
        raise RuntimeError('Selected river-pebble channel contract differs')
    for channel in CHANNELS:
        info=record['maps'][channel]
        if (info['runtime_name']!=('T_EnvironmentRiverPebblesBC8_BaseColor' if channel=='BaseColor' else 'T_EnvironmentRiverPebbles_'+channel) or info['width']!=2048
                or info['height']!=2048 or (channel=='Height' and info['bit_depth']!=16)):
            raise RuntimeError('Selected river-pebble identity/precision differs: '+channel)
    if not record['maps']['Normal']['normal_convention'].startswith('DirectX'):
        raise RuntimeError('The source normal convention must remain DirectX')


def validate_provenance(root,source,manifest):
    hashes={}
    records=list(manifest['licenses'])
    for metadata in manifest['metadata'].values(): records.extend(metadata.values())
    records.extend(manifest['materials']['pebbles']['originals'].values())
    for info in records:
        path=(source/info['path']).resolve()
        if not path.is_relative_to(source): raise RuntimeError('Source provenance path escapes its owner')
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=info['sha256']: raise RuntimeError('Source provenance hash differs: '+str(path))
        hashes[str(path.relative_to(root))]=actual
    for key,hashkey in [('generator_source','generator_sha256'),('required_helper','required_helper_sha256')]:
        path=(root/manifest[key]).resolve()
        if not path.is_relative_to(root/'Tools/UsfMaterials'): raise RuntimeError('Source generator path escapes tools')
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=manifest[hashkey]: raise RuntimeError('Source recipe changed after its receipt')
        hashes[str(path.relative_to(root))]=actual
    derivation=manifest['runtime_color_derivation']
    recipe=(root/derivation['recipe_source']).resolve()
    if not recipe.is_relative_to(root/'Tools/UsfMaterials') or hashlib.sha256(recipe.read_bytes()).hexdigest()!=derivation['recipe_sha256']:
        raise RuntimeError('Runtime color recipe differs from receipt')
    hashes[str(recipe.relative_to(root))]=derivation['recipe_sha256']
    original=(source/derivation['source_path']).resolve()
    if not original.is_relative_to(source) or hashlib.sha256(original.read_bytes()).hexdigest()!=derivation['source_sha256']:
        raise RuntimeError('Original encoded-color source differs')
    if derivation['gamma_transform'] is not False or derivation['resize'] is not False or derivation['max_encoded_error']>.5/255:
        raise RuntimeError('Runtime color conversion exceeded encoded quantization contract')
    return hashes


def prepare():
    # This tool is source-only until the lead accepts the selected river-pebble source-art preview.
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('End PIE before importing the selected river-pebble source')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    source = (root / 'Plugins/CkTests/Resources/CkUsf/PebbleReferenceV1').resolve()
    manifest_file = source / 'Manifest-runtime-v2.json'
    manifest_bytes = manifest_file.read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8'))
    validate_manifest(manifest)
    maps=manifest['materials']['pebbles']['maps']
    provenance = validate_provenance(root, source, manifest)
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    destination = '/CkFoundation/CkUsf/Textures/Environment'
    candidates = []
    # Complete every source and destination ownership check before the first asset mutation.
    for channel in CHANNELS:
        info = maps[channel]
        filename = (source / info['path']).resolve()
        if not filename.is_relative_to(source):
            raise RuntimeError('Woodland texture source escapes the selected river-pebble directory')
        data = filename.read_bytes()
        source_hash = hashlib.sha256(data).hexdigest()
        if (source_hash != info['sha256'] or len(data) < 25 or data[:8] != b'\x89PNG\r\n\x1a\n'
                or data[12:16] != b'IHDR' or struct.unpack('>II', data[16:24]) != (info['width'], info['height'])
                or data[24] != info['bit_depth']):
            raise RuntimeError('Woodland PNG hash/dimensions/precision differs: ' + channel)
        name = info['runtime_name']
        path = destination + '/' + name
        texture = unreal.load_asset(path)
        if not texture and unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError('Existing river-pebble destination cannot be loaded for ownership validation')
        if texture and (not isinstance(texture, unreal.Texture2D)
                        or unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256') != source_hash
                        or unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.Manifest') != manifest_tag(channel)):
            raise RuntimeError('Existing river-pebble texture ownership differs; preserve it: ' + path)
        candidates.append((filename, channel, name, path, texture, source_hash, info))
    grid = preflight_grid(root)
    master_path = '/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_EnvironmentRiverPebbles'
    existing_master = unreal.load_asset(master_path)
    if not existing_master and unreal.EditorAssetLibrary.does_asset_exist(master_path):
        raise RuntimeError('Existing river-pebble master cannot be loaded for ownership validation')
    if existing_master:
        if not isinstance(existing_master,unreal.Material): raise RuntimeError('Master destination type differs')
        current_tag=unreal.EditorAssetLibrary.get_metadata_tag(existing_master,'CkUsfRiverPebbles.Manifest')
        current_hash=unreal.EditorAssetLibrary.get_metadata_tag(existing_master,'CkUsfRiverPebbles.ManifestSHA256')
        selected=current_tag==MANIFEST_TAG and current_hash==manifest_hash
        old_hash=hashlib.sha256((source/'Manifest.json').read_bytes()).hexdigest()
        previous=current_tag==ORIGINAL_TAG and current_hash==old_hash
        if not selected and not previous: raise RuntimeError('Unowned master collision; preserve it')
        if previous:
            backup=root/'Saved/UsfMaterialGallery/RiverPebbles-Initial16Bit/M_CkUsf_Look_EnvironmentRiverPebbles.uasset'
            current=root/'Plugins/CkFoundation/Content/CkUsf/GeneratedLooks/M_CkUsf_Look_EnvironmentRiverPebbles.uasset'
            if not backup.is_file() or backup.read_bytes()!=current.read_bytes():
                raise RuntimeError('Original owned master backup must match before color-transfer upgrade')

    # The already verified 80 cm mesh is shared by the two environment looks. Do not resave it.
    mesh=grid[3]
    if not mesh: raise RuntimeError('Prepare the owned river-pebble grid before the river-pebble look')
    if mesh.get_editor_property('nanite_settings').get_editor_property('enabled'):
        raise RuntimeError('The height grid must remain non-Nanite')
    if mesh.get_editor_property('positive_bounds_extension')!=unreal.Vector(0,0,6) or mesh.get_editor_property('negative_bounds_extension')!=unreal.Vector(0,0,6):
        raise RuntimeError('The shared grid displacement bounds changed')
    expected_grid=json.loads((root/'Saved/UsfMaterialGallery/WoodlandPreparation.json').read_text())['grid']['asset_sha256']
    if hashlib.sha256((root/'Plugins/CkTests/Content/CkUsf/Showcase/SM_UsfWoodlandGrid.uasset').read_bytes()).hexdigest()!=expected_grid:
        raise RuntimeError('Shared grid binary differs from the verified previous source')
    grid_receipt={'path':grid[2], 'source_receipt':grid[1], 'reused_without_resave':True,
                  'asset_sha256':hashlib.sha256((root/'Plugins/CkTests/Content/CkUsf/Showcase/SM_UsfWoodlandGrid.uasset').read_bytes()).hexdigest()}

    prepared = []
    for filename, channel, name, path, texture, source_hash, info in candidates:
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
            if len(objects) != 1 or not isinstance(objects[0], unreal.Texture2D) or objects[0].get_path_name() != path + '.' + name:
                raise RuntimeError('Woodland import did not return exactly the owned target texture')
            texture = objects[0]
        settings = {
            # Compression precedes sRGB so false-positive normal detection cannot clear BC gamma.
            'compression_settings': _compression(channel),
            'lod_group': (unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if channel == 'Normal' else
                          unreal.TextureGroup.TEXTUREGROUP_WORLD if channel == 'BaseColor' else unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR),
            'srgb': channel == 'BaseColor',
            'address_x': unreal.TextureAddress.TA_CLAMP,
            'address_y': unreal.TextureAddress.TA_CLAMP,
            'mip_gen_settings': unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,
            'flip_green_channel': False,
            'power_of_two_mode': unreal.TexturePowerOfTwoSetting.NONE,
        }
        for key, value in settings.items():
            texture.set_editor_property(key, value)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256', source_hash)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.Manifest', manifest_tag(channel))
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture):
            raise RuntimeError('Failed saving river-pebble texture: ' + path)
        saved = unreal.load_asset(path)
        size = [info['width'], info['height']]
        if (not saved or _settings(saved) != settings
                or [saved.blueprint_get_size_x(), saved.blueprint_get_size_y()] != size):
            raise RuntimeError('Saved river-pebble texture settings/size differ: ' + path)
        prepared.append({'path': path, 'sha256': source_hash, 'manifest': manifest_tag(channel),
                         'source_size': size, 'runtime_size': size, 'source_png_bit_depth': info['bit_depth'],
                         'saved_settings': {key: value if isinstance(value, bool) else str(value)
                                            for key, value in _settings(saved).items()},
                         'settings_verified_after_save': True})
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Ck_Usf_GenerateLooks ' + LOOK_NAME)
    material = unreal.load_asset(master_path)
    if not material or not isinstance(material, unreal.Material):
        raise RuntimeError('The EnvironmentRiverPebbles master was not generated')
    if set(map(str, unreal.MaterialEditingLibrary.get_texture_parameter_names(material))) != {channel + 'Map' for channel in CHANNELS}:
        raise RuntimeError('Woodland master must expose exactly the five recorded texture parameters')
    for channel in CHANNELS:
        bound = unreal.MaterialEditingLibrary.get_material_default_texture_parameter_value(material, channel + 'Map')
        name = maps[channel]['runtime_name']
        if not bound or bound.get_path_name() != destination + '/' + name + '.' + name:
            raise RuntimeError('Woodland master has a missing/default/wrong texture binding: ' + channel)
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CkUsfRiverPebbles.Manifest', MANIFEST_TAG)
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CkUsfRiverPebbles.ManifestSHA256', manifest_hash)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material):
        raise RuntimeError('Failed saving river-pebble master provenance')
    stats = unreal.MaterialEditingLibrary.get_statistics(material)
    statistics = {field: getattr(stats, field) for field in ['num_pixel_shader_instructions',
                  'num_vertex_shader_instructions', 'num_samplers', 'num_uv_scalars']}
    output = root / 'Saved/UsfMaterialGallery/RiverPebblesPreparation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'selected_source': 'PebbleReferenceV1', 'manifest': MANIFEST_TAG,
                      'manifest_sha256': manifest_hash, 'retained_rejected_look':'EnvironmentWoodland assets and source remain unchanged',
                      'height': {'authored_relief_cm':5.48848,'meaning':'Normal-consistency estimate; not calibrated source depth'}, 'physical_size_cm': [80, 80], 'height_mip_initial': 0,
                      'source_provenance_sha256': provenance,
                      'textures': prepared, 'statistics': {LOOK_NAME: statistics}, 'grid': grid_receipt}, indent=2), encoding='utf-8')
    unreal.log('USF_RIVER_PEBBLES_PREPARED ' + str(output))


if __name__ == '__main__':
    prepare()


