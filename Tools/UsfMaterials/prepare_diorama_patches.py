"""Import only the three new owned diorama looks outside PIE; never resave the shared grid."""
import hashlib
import json
import math
from pathlib import Path
import struct
import unreal
from prepare_woodland import preflight_grid, _compression, _settings
from diorama_settings import presentation

TAG = 'CkTests/Resources/CkUsf/DioramaPatchesV1/Manifest.json'
CHANNELS = ['BaseColor', 'Normal', 'Roughness', 'Height', 'AO']
LOOKS = {'grass':'EnvironmentDioramaGrass', 'dirt':'EnvironmentDioramaDirt', 'mud':'EnvironmentDioramaMud'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('End PIE and collect the old world before preparing dioramas')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    source = root/'Plugins/CkTests/Resources/CkUsf/DioramaPatchesV1'
    manifest_path = source/'Manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest_hash = digest(manifest_path)
    if manifest['schema_version'] != 1 or set(manifest['materials']) != set(LOOKS):
        raise RuntimeError('Expected exactly the three declared diorama source materials')
    provenance = {}

    def checked(info):
        path = (source/info['path']).resolve()
        if not path.is_relative_to(source) or digest(path) != info['sha256']:
            raise RuntimeError('Source identity differs: '+str(path))
        provenance[str(path.relative_to(root))] = info['sha256']
        return path

    generator = root/manifest['generator_source']
    if generator.resolve() != root/'Tools/UsfMaterials/author_diorama_patches.py' or digest(generator) != manifest['generator_sha256']:
        raise RuntimeError('Diorama authoring recipe changed after baking')
    provenance[str(generator.relative_to(root))] = digest(generator)
    helper=(root/manifest['helper_source']).resolve()
    if helper != root/'Tools/UsfMaterials/author_woodland_patch.py' or digest(helper)!=manifest['helper_sha256']:
        raise RuntimeError('Verified authoring helper changed after baking')
    provenance[str(helper.relative_to(root))]=digest(helper)
    for info in manifest.get('provenance_evidence', []):
        checked(info)
    for relative,expected in manifest['licensed_source_sha256'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root/'Plugins/CkTests/Resources/CkUsf') or digest(path)!=expected:
            raise RuntimeError('Licensed source input changed: '+relative)
        provenance[str(path.relative_to(root))]=expected
    grid = preflight_grid(root)
    mesh = grid[3]
    grid_file = root/'Plugins/CkTests/Content/CkUsf/Showcase/SM_UsfWoodlandGrid.uasset'
    old_grid = json.loads((root/'Saved/UsfMaterialGallery/WoodlandPreparation.json').read_text())['grid']
    if (not mesh or digest(grid_file) != old_grid['asset_sha256']
            or mesh.get_editor_property('nanite_settings').get_editor_property('enabled')
            or any(mesh.get_editor_property(k) != unreal.Vector(0,0,6) for k in ['positive_bounds_extension','negative_bounds_extension'])):
        raise RuntimeError('The protected dense grid no longer matches its verified state')
    destination = '/CkFoundation/CkUsf/Textures/Environment'
    candidates, masters = [], {}
    # Validate every source and every collision before any import/save.
    for key, look in LOOKS.items():
        record = manifest['materials'][key]
        relief = record['height']['range_cm']
        if (record['look_id'] != look or set(record['maps']) != set(CHANNELS)
                or record['physical_width_cm'] != 80 or record['physical_height_cm'] != 80
                or not math.isfinite(relief) or not 0 < relief <= 6):
            raise RuntimeError('Diorama identity/physical extent/height differs: '+key)
        if not {'BaseColor','WorldNormal','Roughness','HeightCm','AO'} <= set(record['masters']):
            raise RuntimeError('Missing aligned source EXR masters')
        if not str(record['maps']['Normal'].get('normal_convention','')).startswith('DirectX'):
            raise RuntimeError('Diorama normal must declare the verified DirectX convention')
        resolution=record['maps']['BaseColor']['width']
        checked(record['blend'])
        for info in record['masters'].values(): checked(info)
        for channel in CHANNELS:
            info = record['maps'][channel]
            filename = checked(info)
            data = filename.read_bytes()
            if (info['runtime_name'] != 'T_'+look+'_'+channel or data[:8] != b'\x89PNG\r\n\x1a\n'
                    or struct.unpack('>II', data[16:24]) != (info['width'],info['height'])
                    or data[24] != info['bit_depth'] or info['width'] != info['height']
                    or info['width'] != resolution or info['width'] < 1024 or info['width'] & (info['width']-1)
                    or info['bit_depth'] not in ([8] if channel=='BaseColor' else [16] if channel=='Height' else [8,16])
                    or info['color_space'] != ('sRGB' if channel=='BaseColor' else 'linear')):
                raise RuntimeError('Aligned map dimensions/precision/color contract differs: '+key+'/'+channel)
            name = info['runtime_name']; path = destination+'/'+name
            texture = unreal.load_asset(path)
            if unreal.EditorAssetLibrary.does_asset_exist(path) and not texture:
                raise RuntimeError('Existing texture cannot load: '+path)
            if texture and (not isinstance(texture,unreal.Texture2D)
                    or unreal.EditorAssetLibrary.get_metadata_tag(texture,'CkUsfLibrary.SourceSHA256') != info['sha256']
                    or unreal.EditorAssetLibrary.get_metadata_tag(texture,'CkUsfLibrary.Manifest') != TAG):
                raise RuntimeError('Unowned texture collision: '+path)
            candidates.append((key,channel,filename,name,path,texture,info))
        path = '/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_'+look
        master = unreal.load_asset(path)
        if (unreal.EditorAssetLibrary.does_asset_exist(path) and not master) or (master and
                (not isinstance(master,unreal.Material)
                 or unreal.EditorAssetLibrary.get_metadata_tag(master,'CkUsfDiorama.ManifestSHA256') != manifest_hash)):
            raise RuntimeError('Unowned master collision: '+path)
        masters[key] = path
    textures = []
    for key,channel,filename,name,path,texture,info in candidates:
        if not texture:
            task = unreal.AssetImportTask()
            task.filename=str(filename); task.destination_path=destination; task.destination_name=name
            task.automated=True; task.save=False; task.replace_existing=False
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objects=task.get_objects()
            if len(objects)!=1 or not isinstance(objects[0],unreal.Texture2D) or objects[0].get_path_name()!=path+'.'+name:
                raise RuntimeError('Import did not return the exact owned texture')
            texture=objects[0]
        settings={'compression_settings':_compression(channel),
                  'lod_group':unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if channel=='Normal' else
                  unreal.TextureGroup.TEXTUREGROUP_WORLD if channel=='BaseColor' else unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR,
                  'srgb':channel=='BaseColor','address_x':unreal.TextureAddress.TA_CLAMP,'address_y':unreal.TextureAddress.TA_CLAMP,
                  'mip_gen_settings':unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,'flip_green_channel':False,
                  'power_of_two_mode':unreal.TexturePowerOfTwoSetting.NONE}
        for field,value in settings.items(): texture.set_editor_property(field,value)
        unreal.EditorAssetLibrary.set_metadata_tag(texture,'CkUsfLibrary.SourceSHA256',info['sha256'])
        unreal.EditorAssetLibrary.set_metadata_tag(texture,'CkUsfLibrary.Manifest',TAG)
        if (not unreal.EditorAssetLibrary.save_loaded_asset(texture) or _settings(texture)!=settings
                or [texture.blueprint_get_size_x(),texture.blueprint_get_size_y()] != [info['width'],info['height']]):
            raise RuntimeError('Saved texture settings differ: '+path)
        textures.append({'patch':key,'channel':channel,'path':path,'source_sha256':info['sha256'],
                         'source_size':[info['width'],info['height']],
                         'runtime_size':[texture.blueprint_get_size_x(),texture.blueprint_get_size_y()],
                         'settings':{k:v if isinstance(v,bool) else str(v) for k,v in settings.items()}})
    statistics={}
    for key,look in LOOKS.items():
        unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Ck_Usf_GenerateLooks '+look)
        material=unreal.load_asset(masters[key])
        if not isinstance(material,unreal.Material) or set(map(str,unreal.MaterialEditingLibrary.get_texture_parameter_names(material)))!={c+'Map' for c in CHANNELS}:
            raise RuntimeError('Missing generated master or texture parameters: '+look)
        for channel,info in manifest['materials'][key]['maps'].items():
            bound=unreal.MaterialEditingLibrary.get_material_default_texture_parameter_value(material,channel+'Map')
            if not bound or bound.get_path_name()!=destination+'/'+info['runtime_name']+'.'+info['runtime_name']:
                raise RuntimeError('Generated texture binding differs: '+look+'/'+channel)
        unreal.EditorAssetLibrary.set_metadata_tag(material,'CkUsfDiorama.ManifestSHA256',manifest_hash)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material): raise RuntimeError('Master save failed')
        stats=unreal.MaterialEditingLibrary.get_statistics(material)
        statistics[look]={k:getattr(stats,k) for k in ['num_pixel_shader_instructions','num_vertex_shader_instructions','num_samplers']}
    result={'manifest_sha256':manifest_hash,'provenance_sha256':provenance,'textures':textures,'masters':masters,
            'presentation':{key:presentation(record) for key,record in manifest['materials'].items()},
            'statistics':statistics,'grid':{'path':grid[2],'asset_sha256':digest(grid_file),'reused_without_resave':True}}
    (root/'Saved/UsfMaterialGallery/DioramaPreparation.json').write_text(json.dumps(result,indent=2))
    unreal.log('USF_DIORAMAS_PREPARED')
