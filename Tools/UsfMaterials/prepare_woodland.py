"""Validate and import the selected V3 woodland patch, then generate its master outside PIE."""
from pathlib import Path
import hashlib
import json
import math
import struct
import unreal


LOOK_NAME = 'EnvironmentWoodland'
MANIFEST_TAG = 'CkTests/Resources/CkUsf/WoodlandPatchV3/Manifest.json'
CHANNELS = ['BaseColor', 'Normal', 'Roughness', 'Height', 'AO']


def preflight_grid(root):
    import importlib.util
    spec = importlib.util.spec_from_file_location('ck_usf_owned_woodland_grid', root / 'Tools/UsfMaterials/generate_woodland_grid.py')
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
            raise RuntimeError('Existing woodland destination is not a StaticMesh; preserve it')
        import_data = mesh.get_editor_property('asset_import_data')
        if (not import_data
                or unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.SourceSHA256') != canonical['sha256']
                or unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.Generator') != canonical['generator']
                or Path(import_data.get_first_filename()).resolve() != source.resolve()):
            raise RuntimeError('Existing woodland mesh ownership/source differs; preserve it')
    return source, canonical, destination, mesh


def import_grid(grid):
    source, canonical, destination, mesh = grid
    name = destination.rsplit('/', 1)[-1]
    if not mesh:
        options = unreal.FbxImportUI()
        options.import_mesh = True
        options.import_materials = False
        options.import_textures = False
        options.static_mesh_import_data.combine_meshes = True
        options.static_mesh_import_data.auto_generate_collision = False
        options.static_mesh_import_data.convert_scene = False
        options.static_mesh_import_data.set_editor_property('coordinate_system_policy', unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES)
        options.static_mesh_import_data.convert_scene_unit = False
        options.static_mesh_import_data.import_rotation = unreal.Rotator(0, 0, 0)
        options.static_mesh_import_data.import_translation = unreal.Vector(0, 0, 0)
        options.static_mesh_import_data.import_uniform_scale = 1.0
        options.static_mesh_import_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task = unreal.AssetImportTask()
        task.filename = str(source)
        task.destination_path = '/CkTests/CkUsf/Showcase'
        task.destination_name = name
        task.automated = True
        task.save = False
        task.replace_existing = False
        task.replace_existing_settings = True
        task.factory = unreal.FbxFactory()
        task.options = options
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects = task.get_objects()
        if len(objects) != 1 or objects[0].get_path_name() != destination + '.' + name:
            raise RuntimeError('Ground import did not return exactly the owned target mesh')
        mesh = objects[0]
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError('Ground import is not a StaticMesh')
    slots = [str(slot.material_slot_name) for slot in mesh.static_materials]
    if slots.count('Specimen') != 1 or slots.count('CoreBase') != 1:
        raise RuntimeError('Ground mesh requires unique named Specimen/CoreBase slots')
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sections = {}
    for lod in range(subsystem.get_lod_count(mesh)):
        sections[lod] = [subsystem.get_lod_material_slot(mesh, lod, section)
                         for section in range(mesh.get_num_sections(lod))]
        if (len(sections[lod]) != 2 or any(index < 0 or index >= len(slots) for index in sections[lod])
                or {slots[index] for index in sections[lod]} != {'Specimen', 'CoreBase'}):
            raise RuntimeError('Ground LOD sections must use exactly Specimen/CoreBase')
    if not sections:
        raise RuntimeError('Ground mesh has no valid LOD sections')
    unused = [name for index, name in enumerate(slots) if not any(index in indices for indices in sections.values())]
    if unused not in [[], ['defaultMat']]:
        raise RuntimeError('Woodland mesh contains an unexpected unused material slot')
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.set_editor_property('enabled', False)
    mesh.set_editor_property('nanite_settings', nanite)
    # WPO can recess the top by at most 6 cm; the entire slab stays at -6.5/-9.
    # Keep an additional 6 cm allowance in each direction for explicit displacement bounds.
    mesh.set_editor_property('positive_bounds_extension', unreal.Vector(0, 0, 6))
    mesh.set_editor_property('negative_bounds_extension', unreal.Vector(0, 0, 6))
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, 'CkUsfEnvironment.SourceSHA256', canonical['sha256'])
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, 'CkUsfEnvironment.Generator', canonical['generator'])
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh):
        raise RuntimeError('Failed saving owned ground mesh')
    saved = unreal.load_asset(destination)
    if not saved or saved.get_editor_property('nanite_settings').get_editor_property('enabled'):
        raise RuntimeError('Ground Nanite settings were not preserved')
    for field in ['positive_bounds_extension', 'negative_bounds_extension']:
        if saved.get_editor_property(field) != unreal.Vector(0, 0, 6):
            raise RuntimeError('Ground displacement bounds were not preserved')
    asset = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / 'Plugins/CkTests/Content/CkUsf/Showcase' / (name + '.uasset')
    return {'path': destination, 'source': str(source), 'source_receipt': canonical,
            'asset_sha256': hashlib.sha256(asset.read_bytes()).hexdigest(), 'slots': slots,
            'section_material_indices': sections,
            'unused_slots': [name for index, name in enumerate(slots)
                             if not any(index in indices for indices in sections.values())],
            'positive_bounds_extension': [0, 0, 6], 'negative_bounds_extension': [0, 0, 6],
            'nanite': False, 'runtime_topology_and_uv_basis_require_rendered_validation': True}


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
    if manifest['look_id'] != LOOK_NAME or manifest['schema_version'] != 1 or set(manifest['maps']) != set(CHANNELS):
        raise RuntimeError('Woodland V3 requires its exact look/schema and all five actual maps')
    if manifest['physical_width_cm'] != 80 or manifest['physical_height_cm'] != 80:
        raise RuntimeError('Woodland texture footprint must be exactly 80 by 80 centimeters')
    height = manifest['height']
    values = [height[key] for key in ['z_min_cm', 'z_max_cm', 'range_cm']]
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise RuntimeError('Woodland height calibration must be finite')
    low, high, span = values
    if (not 0 < span <= 6 or not math.isclose(high - low, span, rel_tol=1e-6, abs_tol=1e-6)
            or height.get('not_albedo_derived') is not True
            or height.get('decode') != 'height_cm=z_min_cm+sampleHeight16*range_cm'):
        raise RuntimeError('Woodland height must be geometry-derived, normalized and calibrated within six centimeters')
    if not str(manifest['normal']['normal_convention']).startswith('DirectX'):
        raise RuntimeError('Woodland requires the aligned DirectX normal bake without a green flip')
    resolution = manifest['prototype_resolution']
    if type(resolution) is not int or resolution <= 0 or resolution & (resolution - 1):
        raise RuntimeError('Aligned woodland data must use a power-of-two source resolution; no runtime resampling')
    for channel in CHANNELS:
        info = manifest['maps'][channel]
        if (info['runtime_name'] != 'T_EnvironmentWoodland_' + channel
                or info['width'] != resolution or info['height'] != resolution
                or info['color_space'] != ('sRGB' if channel == 'BaseColor' else 'linear')
                or info['bit_depth'] not in ([16] if channel == 'Height' else [8, 16])):
            raise RuntimeError('Woodland aligned-map identity/color/precision contract differs: ' + channel)


def validate_provenance(root, source, manifest):
    hashes = {}

    def checked_file(base, info, suffix):
        path = (base / info['path']).resolve()
        if not path.is_relative_to(base.resolve()) or path.suffix.lower() != suffix:
            raise RuntimeError('Woodland provenance path escapes its owner or has the wrong format')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != info['sha256']:
            raise RuntimeError('Woodland provenance hash differs: ' + str(path))
        hashes[str(path.relative_to(root))] = actual

    checked_file(source, manifest['blend'], '.blend')
    masters = manifest['masters']
    if not {'BaseColor', 'WorldNormal', 'Roughness', 'HeightCm', 'AO'} <= set(masters):
        raise RuntimeError('Woodland provenance requires every aligned EXR master')
    for info in masters.values():
        checked_file(source, info, '.exr')
    generator = (root / manifest['generator_source']).resolve()
    if not generator.is_relative_to((root / 'Tools/UsfMaterials').resolve()) or generator.suffix != '.py':
        raise RuntimeError('Woodland generator source must be the pinned repository authoring script')
    actual = hashlib.sha256(generator.read_bytes()).hexdigest()
    if actual != manifest['generator_sha256']:
        raise RuntimeError('Woodland authoring generator no longer matches the selected source manifest')
    hashes[str(generator.relative_to(root))] = actual
    return hashes


def prepare():
    # This tool is source-only until the lead accepts the selected V3 source-art preview.
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('End PIE before importing the approved woodland source')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    source = (root / 'Plugins/CkTests/Resources/CkUsf/WoodlandPatchV3').resolve()
    manifest_file = source / 'Manifest.json'
    manifest_bytes = manifest_file.read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8'))
    validate_manifest(manifest)
    provenance = validate_provenance(root, source, manifest)
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    destination = '/CkFoundation/CkUsf/Textures/Environment'
    candidates = []
    # Complete every source and destination ownership check before the first asset mutation.
    for channel in CHANNELS:
        info = manifest['maps'][channel]
        filename = (source / info['path']).resolve()
        if not filename.is_relative_to(source):
            raise RuntimeError('Woodland texture source escapes the selected V3 directory')
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
            raise RuntimeError('Existing woodland destination cannot be loaded for ownership validation')
        if texture and (not isinstance(texture, unreal.Texture2D)
                        or unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.SourceSHA256') != source_hash
                        or unreal.EditorAssetLibrary.get_metadata_tag(texture, 'CkUsfLibrary.Manifest') != MANIFEST_TAG):
            raise RuntimeError('Existing woodland texture ownership differs; preserve it: ' + path)
        candidates.append((filename, channel, name, path, texture, source_hash, info))
    grid = preflight_grid(root)
    master_path = '/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_EnvironmentWoodland'
    existing_master = unreal.load_asset(master_path)
    if not existing_master and unreal.EditorAssetLibrary.does_asset_exist(master_path):
        raise RuntimeError('Existing woodland master cannot be loaded for ownership validation')
    if existing_master and (not isinstance(existing_master, unreal.Material)
                            or unreal.EditorAssetLibrary.get_metadata_tag(existing_master, 'CkUsfWoodland.Manifest') != MANIFEST_TAG
                            or unreal.EditorAssetLibrary.get_metadata_tag(existing_master, 'CkUsfWoodland.ManifestSHA256') != manifest_hash):
        raise RuntimeError('Existing woodland master is not owned by this selected V3 import; preserve it')

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
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'CkUsfLibrary.Manifest', MANIFEST_TAG)
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture):
            raise RuntimeError('Failed saving woodland texture: ' + path)
        saved = unreal.load_asset(path)
        size = [info['width'], info['height']]
        if (not saved or _settings(saved) != settings
                or [saved.blueprint_get_size_x(), saved.blueprint_get_size_y()] != size):
            raise RuntimeError('Saved woodland texture settings/size differ: ' + path)
        prepared.append({'path': path, 'sha256': source_hash, 'manifest': MANIFEST_TAG,
                         'source_size': size, 'runtime_size': size, 'source_png_bit_depth': info['bit_depth'],
                         'saved_settings': {key: value if isinstance(value, bool) else str(value)
                                            for key, value in _settings(saved).items()},
                         'settings_verified_after_save': True})
    grid_receipt = import_grid(grid)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Ck_Usf_GenerateLooks ' + LOOK_NAME)
    material = unreal.load_asset(master_path)
    if not material or not isinstance(material, unreal.Material):
        raise RuntimeError('The EnvironmentWoodland master was not generated')
    if set(map(str, unreal.MaterialEditingLibrary.get_texture_parameter_names(material))) != {channel + 'Map' for channel in CHANNELS}:
        raise RuntimeError('Woodland master must expose exactly the five recorded texture parameters')
    for channel in CHANNELS:
        bound = unreal.MaterialEditingLibrary.get_material_default_texture_parameter_value(material, channel + 'Map')
        name = manifest['maps'][channel]['runtime_name']
        if not bound or bound.get_path_name() != destination + '/' + name + '.' + name:
            raise RuntimeError('Woodland master has a missing/default/wrong texture binding: ' + channel)
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CkUsfWoodland.Manifest', MANIFEST_TAG)
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CkUsfWoodland.ManifestSHA256', manifest_hash)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material):
        raise RuntimeError('Failed saving woodland master provenance')
    stats = unreal.MaterialEditingLibrary.get_statistics(material)
    statistics = {field: getattr(stats, field) for field in ['num_pixel_shader_instructions',
                  'num_vertex_shader_instructions', 'num_samplers', 'num_uv_scalars']}
    output = root / 'Saved/UsfMaterialGallery/WoodlandPreparation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'selected_source': 'WoodlandPatchV3', 'manifest': MANIFEST_TAG,
                      'manifest_sha256': manifest_hash, 'unused_drafts': ['WoodlandPatchV1; art rejected and never imported by this tool',
                                         'WoodlandPatchV2; art rejected and never imported by this tool'],
                      'height': manifest['height'], 'physical_size_cm': [80, 80], 'height_mip_initial': 0,
                      'source_provenance_sha256': provenance,
                      'textures': prepared, 'statistics': {LOOK_NAME: statistics}, 'grid': grid_receipt}, indent=2), encoding='utf-8')
    unreal.log('USF_WOODLAND_PREPARED ' + str(output))


if __name__ == '__main__':
    prepare()


