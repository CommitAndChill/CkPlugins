"""Validate and import the recorded gravel environment look, then generate their masters outside PIE."""
from pathlib import Path
import hashlib
import json
import struct
import unreal


LOOKS = {'gravel': 'EnvironmentGravel'}
MANIFEST_TAG = 'CkTests/Resources/CkUsf/Environment1Textures/Manifest.json'


def preflight_grid(root):
    import importlib.util
    spec = importlib.util.spec_from_file_location('ck_usf_owned_environment_grid', root / 'Tools/UsfMaterials/generate_environment_grid.py')
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
    replace_failed = False
    upgrade_owned = False
    if mesh:
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError('Existing ground destination is not a StaticMesh')
        # Failed v1/v2 imports were deliberately not saved. Recover only these exact owned
        # attempts; preserve old source bytes and never replace an existing asset file.
        import_data = mesh.get_editor_property('asset_import_data')
        if not import_data:
            raise RuntimeError('Existing ground mesh has no recorded import source')
        imported_from = Path(import_data.get_first_filename()).resolve()
        recoverable = {
            (generator.DIRECTORY / (generator.NAME + '.obj')).resolve():
                ('bd96b0eab6fe4d938c30d14e6eb57954dd72b3d5ae0f6accc62ba70ba19d2cb0', ['defaultMat']),
            (generator.DIRECTORY / (generator.NAME + '_v2.obj')).resolve():
                ('41bf351ee3cb7088d3d3f668a8fb6d3be64d17cd9428934d061825be7d0d07b1', ['defaultMat', 'CoreBase', 'Specimen'])}
        failed = recoverable.get(imported_from)
        asset_file = root / 'Plugins/CkTests/Content/CkUsf/Showcase' / (generator.NAME + '.uasset')
        replace_failed = (
            isinstance(mesh, unreal.StaticMesh) and not asset_file.exists()
            and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.SourceSHA256') == ''
            and failed is not None
            and [str(item.material_slot_name) for item in mesh.static_materials] == failed[1]
            and hashlib.sha256(imported_from.read_bytes()).hexdigest() == failed[0])
        previous_source = (generator.DIRECTORY / (generator.NAME + '_v3.obj')).resolve()
        previous_hash = '15d86b697ac8fd4a970bc60997ea688c5d9b17e3b05f3f8bccd55a26056f545d'
        upgrade_owned = (
            asset_file.is_file() and imported_from == previous_source
            and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.Generator') == 'CkUsf.EnvironmentGrid.v3'
            and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.SourceSHA256') == previous_hash
            and hashlib.sha256(previous_source.read_bytes()).hexdigest() == previous_hash
            and [str(item.material_slot_name) for item in mesh.static_materials] == ['defaultMat', 'CoreBase', 'Specimen'])
        if upgrade_owned:
            backup = root / 'Saved/UsfMaterialGallery/EnvironmentGridV3' / asset_file.name
            data = asset_file.read_bytes()
            if backup.exists() and backup.read_bytes() != data:
                raise RuntimeError('Ground v3 backup differs; preserve both and inspect concurrent changes')
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                backup.write_bytes(data)
        if (not isinstance(mesh, unreal.StaticMesh)
                or unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.SourceSHA256') != canonical['sha256']
                or unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.Generator') != canonical['generator']
                or Path(mesh.get_editor_property('asset_import_data').get_first_filename()).resolve() != source.resolve()) and not (replace_failed or upgrade_owned):
            raise RuntimeError('Existing ground mesh ownership/source differs; preserve it')
    return source, canonical, destination, mesh, replace_failed or upgrade_owned


def import_grid(grid):
    source, canonical, destination, mesh, replace_failed = grid
    name = destination.rsplit('/', 1)[-1]
    if not mesh or replace_failed:
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
        task.replace_existing = replace_failed
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
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.set_editor_property('enabled', False)
    mesh.set_editor_property('nanite_settings', nanite)
    # WPO can recess the top by 12 cm; the slab already extends to -16.
    # Keep an additional 12 cm allowance in each direction for explicit displacement bounds.
    mesh.set_editor_property('positive_bounds_extension', unreal.Vector(0, 0, 12))
    mesh.set_editor_property('negative_bounds_extension', unreal.Vector(0, 0, 12))
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, 'CkUsfEnvironment.SourceSHA256', canonical['sha256'])
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, 'CkUsfEnvironment.Generator', canonical['generator'])
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh):
        raise RuntimeError('Failed saving owned ground mesh')
    saved = unreal.load_asset(destination)
    if not saved or saved.get_editor_property('nanite_settings').get_editor_property('enabled'):
        raise RuntimeError('Ground Nanite settings were not preserved')
    for field in ['positive_bounds_extension', 'negative_bounds_extension']:
        if saved.get_editor_property(field) != unreal.Vector(0, 0, 12):
            raise RuntimeError('Ground displacement bounds were not preserved')
    asset = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / 'Plugins/CkTests/Content/CkUsf/Showcase' / (name + '.uasset')
    return {'path': destination, 'source': str(source), 'source_receipt': canonical,
            'asset_sha256': hashlib.sha256(asset.read_bytes()).hexdigest(), 'slots': slots,
            'section_material_indices': sections,
            'unused_slots': [name for index, name in enumerate(slots)
                             if not any(index in indices for indices in sections.values())],
            'positive_bounds_extension': [0, 0, 12], 'negative_bounds_extension': [0, 0, 12],
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


def prepare():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('End PIE before preparing the environment texture-backed patch')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    source = (root / 'Plugins/CkTests/Resources/CkUsf/Environment1Textures').resolve()
    manifest = json.loads((source / 'Manifest.json').read_text(encoding='utf-8'))
    records = manifest['materials']
    if set(records) != set(LOOKS):
        raise RuntimeError('Environment one must contain exactly its approved gravel material key')
    destination = '/CkFoundation/CkUsf/Textures/Environment'
    candidates = []
    # Complete the source and ownership preflight before importing or changing any asset.
    for key, look_id in LOOKS.items():
        record = records[key]
        if record['look_id'] != look_id:
            raise RuntimeError('Unexpected environment-one look ID: ' + key)
        channels = {'BaseColor', 'Normal', 'Roughness', 'Height'}
        if 'AO' in record['maps']:
            channels.add('AO')
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
            if channel == 'Height' and (data[:8] != b'\x89PNG\r\n\x1a\n' or len(data) < 25 or data[24] != 16):
                raise RuntimeError('Environment height requires the recorded 16-bit PNG source: ' + str(filename))
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

    grid = preflight_grid(root)
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
                         'saved_settings': {key: value if isinstance(value, bool) else str(value)
                                            for key, value in _settings(saved).items()},
                         'source_size': [width, height], 'runtime_size': list(actual_size),
                         'source_png_bit_depth': filename.read_bytes()[24],
                         'source_aspect_ratio': width / height,
                         'runtime_aspect_ratio': actual_size[0] / actual_size[1],
                         'runtime_aspect_changed': resize and width != height,
                         'runtime_resize_for_streaming': resize, 'settings_verified_after_save': True})

    grid_receipt = import_grid(grid)
    statistics = {}
    for look_id in LOOKS.values():
        unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Ck_Usf_GenerateLooks ' + look_id)
        material = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + look_id)
        if not material:
            raise RuntimeError('Master was not generated: ' + look_id)
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        statistics[look_id] = {field: getattr(stats, field) for field in [
            'num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers', 'num_uv_scalars']}
    output = root / 'Saved/UsfMaterialGallery/Environment1Preparation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'textures': prepared, 'statistics': statistics, 'grid': grid_receipt}, indent=2), encoding='utf-8')
    unreal.log('USF_ENVIRONMENT1_PREPARED ' + str(output))


if __name__ == '__main__':
    prepare()
