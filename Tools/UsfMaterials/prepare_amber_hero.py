"""Additive preparation of owned closed amber hero meshes and CC0 leaf materials."""
from pathlib import Path
import hashlib,json
import unreal
from prepare_native_bsdf import _param
from amber_specimen_settings import LOOKS as AMBER_LOOKS
OWNER='CkUsf.AmberHeroPreparation.v1'
ASSET='/CkFoundation/CkUsf'

def prepare():
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Prepare hero outside PIE')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat')!=1:raise RuntimeError('Hero needs Adaptive profile')
    root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    source=root/'Plugins/CkTests/Resources/CkUsf/AmberHeroV1'
    manifest=json.loads((source/'Manifest.json').read_text())
    if set(manifest['meshes'])!={'Body','Leaf','Debris','BubbleSource'}:raise RuntimeError('Exact hero mesh roster required')
    if hashlib.sha256((root/manifest['generator_source']).read_bytes()).hexdigest()!=manifest['generator_sha256']:raise RuntimeError('Hero generator hash differs')
    def owned(path,cls,pin):
        asset=unreal.load_asset(path)
        if unreal.EditorAssetLibrary.does_asset_exist(path) and (not isinstance(asset,cls) or unreal.EditorAssetLibrary.get_metadata_tag(asset,OWNER)!=pin):raise RuntimeError('Preserve differently owned asset: '+path)
        return asset
    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Could not save hero asset')
    entries={}
    for role,record in manifest['meshes'].items():
        file=(source/record['path']).resolve()
        if not file.is_relative_to(source.resolve()) or hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256'] or record['slot']!=role or record['degenerate_triangles']!=0:raise RuntimeError('Hero mesh source validation failed: '+role)
        name='SM_AmberHero_'+role;folder='/CkTests/CkUsf/Showcase/AmberHero'
        entries[role]=dict(file=file,pin=record['sha256'],name=name,folder=folder,path=folder+'/'+name,mesh=True)
    for channel in ['BaseColor','Normal','Roughness','Opacity','Height']:
        file=source/'LeafSource'/('AutumnLeaf31_2K_front_'+channel+'.png')
        data=file.read_bytes()
        if data[:8]!=b'\x89PNG\r\n\x1a\n':raise RuntimeError('Leaf PNG required '+channel)
        name='T_AmberHero_'+channel;folder=ASSET+'/Textures/Optical/AmberHero'
        entries[channel]=dict(file=file,pin=hashlib.sha256(data).hexdigest(),name=name,folder=folder,path=folder+'/'+name,mesh=False)
    # Check every destination before beginning any imports.
    for key,entry in entries.items():entry['asset']=owned(entry['path'],unreal.StaticMesh if entry['mesh'] else unreal.Texture2D,entry['pin'])
    bubble=AMBER_LOOKS['Body']
    scalar=dict(bubble['scalars']);scalar.update(AbsorptionStrength=1,Ior=1.54,ThicknessCm=.015,EdgeThicknessCm=.015,TintVariation=0,DistortionStrength=0,RoughnessBias=.015,RoughnessScale=0)
    recipes={
        'leaf':dict(name='OpticalAmberHeroLeaf',source='AmberHeroLeaf',graph=0,shading=8,blend=2,two_sided=True,
                    textures=[(parameter,entries[channel]['path']) for parameter,channel in [('BaseColorMap','BaseColor'),('NormalMap','Normal'),('RoughnessMap','Roughness'),('OpacityMap','Opacity')]],
                    vectors=[('TintColor',(1,1,1,1))],scalars=[('UVScale',1),('NormalStrength',.7),('RoughnessScale',1),('RoughnessBias',.02),('TransmissionStrength',.7)]),
        'bubble':dict(name='OpticalAmberHeroBubble',source='AmberSpecimen',graph=6,shading=0,blend=0,two_sided=False,
                    textures=[(parameter,ASSET+'/Textures/Optical/Amber/T_AmberSpecimen_'+key) for parameter,key in bubble['textures']],
                    vectors=[('TransmissionColor',(.999,.999,.999,1))],scalars=list(scalar.items()))}
    body_scalar=dict(bubble['scalars']);body_scalar.update(ReferenceThicknessCm=1,ThicknessCm=3.8,EdgeThicknessCm=.3,
        RoughnessScale=.2,RoughnessBias=.025,NormalStrength=.4,DistortionStrength=.008)
    recipes['body']=dict(name='OpticalAmberHeroBody',source='AmberHeroBody',graph=7,shading=0,blend=0,two_sided=False,
        textures=[(parameter,ASSET+'/Textures/Optical/Amber/T_AmberSpecimen_'+key) for parameter,key in bubble['textures']],
        vectors=[('TransmissionColor',(.985,.72,.31,1))],scalars=list(body_scalar.items()))
    for role,recipe in recipes.items():
        recipe['pin']=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest()
        recipe['definition_path']=ASSET+'/Looks/Optical/DA_'+recipe['name']
        recipe['master_path']=ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name']
        recipe['definition']=owned(recipe['definition_path'],unreal.CkUsf_LookDefinition,recipe['pin'])
        master=unreal.load_asset(recipe['master_path'])
        if unreal.EditorAssetLibrary.does_asset_exist(recipe['master_path']) and (not isinstance(master,unreal.Material) or unreal.EditorAssetLibrary.get_metadata_tag(master,'CkUsf.SourceDefinition.v1')!=recipe['definition_path']+'.DA_'+recipe['name']):raise RuntimeError('Preserve differently owned hero master')
        for parameter,path in recipe['textures']:
            if role in ['bubble','body'] and not isinstance(unreal.load_asset(path),unreal.Texture2D):raise RuntimeError('Existing amber optical map missing: '+path)
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    for key,entry in entries.items():
        if entry['asset']:continue
        task=unreal.AssetImportTask();task.filename=str(entry['file']);task.destination_path=entry['folder'];task.destination_name=entry['name'];task.automated=True;task.replace_existing=False;task.save=False
        if entry['mesh']:
            options=unreal.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
            data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=False;data.convert_scene_unit=False;data.import_uniform_scale=1
            data.set_editor_property('coordinate_system_policy',unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES)
            data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            task.factory=unreal.FbxFactory();task.options=options
        tools.import_asset_tasks([task]);objects=task.get_objects()
        if len(objects)!=1 or objects[0].get_path_name()!=entry['path']+'.'+entry['name']:raise RuntimeError('Unexpected hero import destination')
        asset=objects[0]
        if entry['mesh']:
            if key not in [str(item.material_slot_name) for item in asset.static_materials]:raise RuntimeError('Missing hero material slot '+key)
            nanite=asset.get_editor_property('nanite_settings');nanite.set_editor_property('enabled',False);asset.set_editor_property('nanite_settings',nanite)
        else:
            asset.set_editor_property('srgb',key=='BaseColor')
            compression=unreal.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else unreal.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else unreal.TextureCompressionSettings.TC_MASKS
            asset.set_editor_property('compression_settings',compression);asset.set_editor_property('flip_green_channel',False)
            asset.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP);asset.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
        unreal.EditorAssetLibrary.set_metadata_tag(asset,OWNER,entry['pin']);save(asset);entry['asset']=asset
    generator=unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    result={}
    for role,recipe in recipes.items():
        definition=recipe['definition']
        if not definition:
            factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.CkUsf_LookDefinition)
            definition=tools.create_asset('DA_'+recipe['name'],ASSET+'/Looks/Optical',unreal.CkUsf_LookDefinition,factory)
            if not definition:raise RuntimeError('Could not create hero definition')
            parameters=[_param(key,2,unreal.load_asset(path).get_path_name(),i*10) for i,(key,path) in enumerate(recipe['textures'])]
            parameters += [_param(key,1,value,i*10) for i,(key,value) in enumerate(recipe['vectors'])]
            parameters += [_param(key,0,value,i*10) for i,(key,value) in enumerate(recipe['scalars'])]
            for key,value in [('_LookName',recipe['name']),('_UshIncludePath','/CkUsf/Looks/'+recipe['source']+'.ush'),('_UshFunctionName','CkUsf_Look_'+recipe['source']),('_Parameters',parameters),('_TwoSided',recipe['two_sided'])]:definition.set_editor_property(key,value)
            for key,value in [('_SurfaceGraph',recipe['graph']),('_Domain',0),('_ShadingModel',recipe['shading']),('_BlendMode',recipe['blend'])]:definition.set_editor_property(key,type(definition.get_editor_property(key)).cast(value))
            unreal.EditorAssetLibrary.set_metadata_tag(definition,OWNER,recipe['pin']);save(definition)
        master=unreal.load_asset(recipe['master_path'])
        if not master:
            generator.generate_look_material_for(definition);master=unreal.load_asset(recipe['master_path'])
        if not isinstance(master,unreal.Material) or unreal.MaterialEditingLibrary.recompile_material(master):raise RuntimeError('Hero material generation/compile failed: '+role)
        save(master);result[role]=master.get_path_name()
    result['meshes']={role:entries[role]['path'] for role in manifest['meshes']}
    return result
