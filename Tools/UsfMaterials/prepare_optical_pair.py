"""Prepare only hash-pinned optical-pair sources; never create or rebind a scene."""
from pathlib import Path
import copy,hashlib,json,math,struct
import unreal
from prepare_native_bsdf import _param
OWNER='CkUsf.OpticalPairPreparation.v1'
ROLES={'Opal','GlassCover','Panel','Housing','MetalTrim'}
# Exact first-lookdev recipe pins recorded by this session, never loaded from mutable Saved state.
INITIAL_RECIPE_PINS={
    'Opal':'5b6b7c705d3b6d695811f58d17182462d4c632127a04e11e6a3ea21ab03da447',
    'GlassCover':'1943db2acfb8865ef6053aab4f57518674fca70e3e4d4d03debcd095fddf938b',
    'Panel':'a37f792b588fa25f61f9be946a4babe8ae475b4b263fff6ca59a39214a587dcb',
    'Housing':'60600ed2db7e8e26d5f8225558eef882811224053a86a1e6a3b571504883b685',
    'MetalTrim':'9732d05e8e91c28ae9431ecc4aa55787d124ad85c66bd47c429ec9f33dafb849'}
EXPECTED_LOOKS={
    'Opal':('OpticalOpal','OpticalOpal'),
    'GlassCover':('OpticalCoatedGlass','OpticalCoatedGlass'),
    'Panel':('OpticalDisplayPanel','OpticalDisplayPanel'),
    'Housing':('OpticalPairHousing','OpticalTailLampHardware'),
    'MetalTrim':('OpticalPairMetalTrim','OpticalTailLampHardware')}

def _sha(data):return hashlib.sha256(data).hexdigest()

def _initial_recipe(role,recipe):
    initial=copy.deepcopy(recipe)
    scalar_overrides={
        'Opal':{'FlashStrength':.8,'DomainNormalStrength':1,'DomainRoughness':.12,'CoatNormalStrength':.1},
        'GlassCover':{'CoatingIor':1.38,'CoatingThicknessNm':360,'CoatingStrength':.85},
        'Panel':{'EmissionStrength':18}}
    overrides=scalar_overrides.get(role,{})
    initial['scalars']=[(key,overrides.get(key,value)) for key,value in initial['scalars']]
    if role=='Opal':initial['vectors']=[(key,(.75,.80,.82,1) if key=='MilkColor' else value) for key,value in initial['vectors']]
    if _sha(json.dumps(initial,sort_keys=True).encode())!=INITIAL_RECIPE_PINS[role]:raise RuntimeError('Initial optical recipe reconstruction differs from pinned source: '+role)
    return initial

def _verify_initial_parameters(definition,role,recipe,entries):
    initial=_initial_recipe(role,recipe)
    expected=[_param(parameter,2,entries[key]['path']+'.'+entries[key]['name'],i*10) for i,(parameter,key) in enumerate(initial['textures'])]
    expected += [_param(key,1,value,i*10) for i,(key,value) in enumerate(initial['vectors'])]
    expected += [_param(key,0,value,i*10) for i,(key,value) in enumerate(initial['scalars'])]
    actual=list(definition.get_editor_property('_Parameters'))
    if len(actual)!=len(expected):raise RuntimeError('Preserve changed initial optical parameter count: '+role)
    for index,(current,original) in enumerate(zip(actual,expected)):
        label=role+'/'+str(original.get_editor_property('_Name'))+' at index '+str(index)
        for field in ['_Name','_Type','_Group','_SortPriority','_DefaultTexturePath','_PerInstance','_PerInstanceSlot','_CustomPrimitiveData','_CustomPrimitiveDataIndex']:
            if current.get_editor_property(field)!=original.get_editor_property(field):raise RuntimeError('Preserve changed initial optical parameter '+label+'/'+field)
        if not math.isclose(current.get_editor_property('_DefaultScalar'),original.get_editor_property('_DefaultScalar'),rel_tol=0,abs_tol=1e-6):raise RuntimeError('Preserve changed initial optical scalar: '+label)
        current_vector=current.get_editor_property('_DefaultVector');original_vector=original.get_editor_property('_DefaultVector')
        if any(not math.isclose(getattr(current_vector,channel),getattr(original_vector,channel),rel_tol=0,abs_tol=1e-6) for channel in 'rgba'):raise RuntimeError('Preserve changed initial optical vector: '+label)
def prepare(allow_recipe_migration=False):
    from optical_pair_settings import ASSET,LOOKS
    if ASSET!='/CkFoundation/CkUsf' or set(LOOKS)!=ROLES:raise RuntimeError('Optical pair requires exact asset root and five look roles')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Prepare optical pair outside PIE, before scene creation')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat')!=1:raise RuntimeError('Optical pair requires Adaptive profile')
    root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    source=root/'Plugins/CkTests/Resources/CkUsf/OpticalPairV1'
    source_hashes={}
    def checked_file(base,relative,expected):
        path=(base/relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(base.resolve()):raise RuntimeError('Optical source escaped allowed root: '+relative)
        if not path.is_file() or _sha(path.read_bytes())!=expected:raise RuntimeError('Optical source missing/hash differs: '+str(path))
        source_hashes[str(path.relative_to(root))]=expected
        return path
    receipts={}
    for filename in ['Geometry.json','DisplayTextures.json','OpalTextures.json']:
        path=source/filename
        if not path.is_file():raise RuntimeError('Complete source receipt required before preparation: '+filename)
        receipt=json.loads(path.read_text(encoding='utf-8-sig'))
        checked_file(root,receipt['generator_source'],receipt['generator_sha256'])
        source_hashes[str(path.relative_to(root))]=_sha(path.read_bytes());receipts[filename]=receipt
    original=receipts['OpalTextures.json']['source']
    checked_file(source,original['path'],original['sha256'])
    geometry=receipts['Geometry.json']
    if set(geometry['meshes'])!=ROLES-{'Opal'}:raise RuntimeError('Optical geometry requires four exact display mesh roles')
    reused=geometry['opal_reused_body'];checked_file(root,reused['path'],reused['sha256'])
    opal_mesh_path='/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body'
    opal_mesh=unreal.load_asset(opal_mesh_path)
    if not isinstance(opal_mesh,unreal.StaticMesh) or reused['source_slot'] not in [str(item.material_slot_name) for item in opal_mesh.static_materials]:raise RuntimeError('Existing named-slot AmberHero body required for opal; no reimport permitted')
    if unreal.EditorAssetLibrary.get_metadata_tag(opal_mesh,'CkUsf.AmberHeroPreparation.v1')!=reused['sha256']:raise RuntimeError('Preserve differently owned/revised reused AmberHero mesh')
    def owned(path,cls,pin):
        asset=unreal.load_asset(path)
        if unreal.EditorAssetLibrary.does_asset_exist(path) and (not isinstance(asset,cls) or unreal.EditorAssetLibrary.get_metadata_tag(asset,OWNER)!=pin):raise RuntimeError('Preserve differently owned optical destination: '+path)
        return asset
    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Could not save owned optical asset: '+asset.get_path_name())
    entries={}
    for role,record in geometry['meshes'].items():
        file=checked_file(source,record['path'],record['sha256'])
        checked_file(source,record['mtl']['path'],record['mtl']['sha256'])
        if record['slot']!=role or record['degenerate_triangles']!=0:raise RuntimeError('Invalid optical mesh slot/triangles: '+role)
        name='SM_OpticalPair_'+role;folder='/CkTests/CkUsf/Showcase/OpticalPair'
        entries[role]=dict(file=file,pin=record['sha256'],name=name,folder=folder,path=folder+'/'+name,mesh=True,record=record)
    maps={}
    for filename in ['DisplayTextures.json','OpalTextures.json']:
        for key,record in receipts[filename]['maps'].items():
            if key in maps or key in entries:raise RuntimeError('Duplicate optical resource key: '+key)
            file=checked_file(source,record['path'],record['sha256']);data=file.read_bytes()
            if data[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',data[16:24])!=(record['width'],record['height']) or data[24]!=record['bit_depth']:raise RuntimeError('Optical PNG container/dimensions differ: '+key)
            if bool(record['srgb'])!=(key.endswith('BaseColor') or key.endswith('Emission') or key=='OpalColor'):raise RuntimeError('Unexpected optical source color space: '+key)
            name='T_OpticalPair_'+key;folder=ASSET+'/Textures/Optical/Pair'
            maps[key]=record;entries[key]=dict(file=file,pin=record['sha256'],name=name,folder=folder,path=folder+'/'+name,mesh=False,record=record)
    # Validate the entire source and destination batch before the first import.
    for entry in entries.values():entry['asset']=owned(entry['path'],unreal.StaticMesh if entry['mesh'] else unreal.Texture2D,entry['pin'])
    definitions={};recipe_pins={};migrate_roles=set()
    for role,recipe in LOOKS.items():
        if (recipe['name'],recipe['source'])!=EXPECTED_LOOKS[role]:raise RuntimeError('Preserve optical look identity: '+role)
        if recipe['graph']!={'Opal':4,'GlassCover':6}.get(role,0):raise RuntimeError('Unexpected optical graph for '+role)
        for parameter,key in recipe['textures']:
            if key not in maps:raise RuntimeError('Missing recipe texture '+role+'/'+parameter+': '+key)
        shader=root/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'/(recipe['source']+'.ush')
        if not shader.is_file() or ('CkUsf_Look_'+recipe['source']) not in shader.read_text():raise RuntimeError('Optical shader entrypoint missing: '+role)
        pin=_sha(json.dumps(recipe,sort_keys=True).encode());recipe_pins[role]=pin
        path=ASSET+'/Looks/Optical/DA_'+recipe['name']
        definition=unreal.load_asset(path)
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            if not isinstance(definition,unreal.CkUsf_LookDefinition) or definition.get_path_name()!=path+'.DA_'+recipe['name']:raise RuntimeError('Preserve optical definition class/path: '+path)
            prior_pin=unreal.EditorAssetLibrary.get_metadata_tag(definition,OWNER)
            if prior_pin not in {pin,INITIAL_RECIPE_PINS[role]}:raise RuntimeError('Preserve unknown optical recipe pin: '+role)
            for field,expected in [('_LookName',recipe['name']),('_UshIncludePath','/CkUsf/Looks/'+recipe['source']+'.ush'),('_UshFunctionName','CkUsf_Look_'+recipe['source'])]:
                if str(definition.get_editor_property(field))!=expected:raise RuntimeError('Preserve changed optical definition '+role+'/'+field)
            if definition.get_editor_property('_TwoSided')!=recipe['two_sided']:raise RuntimeError('Preserve changed optical two-sided setting: '+role)
            for field,value in [('_SurfaceGraph',recipe['graph']),('_Domain',0),('_ShadingModel',recipe['shading']),('_BlendMode',recipe['blend'])]:
                current=definition.get_editor_property(field)
                if current!=type(current).cast(value):raise RuntimeError('Preserve changed optical topology '+role+'/'+field)
            if prior_pin!=pin:
                _verify_initial_parameters(definition,role,recipe,entries)
                if not allow_recipe_migration:raise RuntimeError('Owned optical defaults require explicit fresh-boot prepare(allow_recipe_migration=True), before scene creation: '+role)
                migrate_roles.add(role)
        definitions[role]=definition
        master_path=ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name'];master=unreal.load_asset(master_path)
        if role in migrate_roles and not isinstance(master,unreal.Material):raise RuntimeError('Known initial optical definition requires its existing owned master before migration: '+role)
        if unreal.EditorAssetLibrary.does_asset_exist(master_path) and (not isinstance(master,unreal.Material) or unreal.EditorAssetLibrary.get_metadata_tag(master,'CkUsf.SourceDefinition.v1')!=path+'.DA_'+recipe['name']):raise RuntimeError('Preserve differently owned optical master: '+master_path)
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    for key,entry in entries.items():
        if entry['asset']:continue
        task=unreal.AssetImportTask();task.filename=str(entry['file']);task.destination_path=entry['folder'];task.destination_name=entry['name'];task.automated=True;task.replace_existing=False;task.save=False
        if entry['mesh']:
            options=unreal.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
            data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=False;data.convert_scene_unit=False;data.import_uniform_scale=1
            data.set_editor_property('coordinate_system_policy',unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES);data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            task.factory=unreal.FbxFactory();task.options=options
        try:tools.import_asset_tasks([task])
        except Exception as error:raise RuntimeError('Optical import failed; preserve completed owned imports and inspect '+key) from error
        objects=task.get_objects()
        if len(objects)!=1 or objects[0].get_path_name()!=entry['path']+'.'+entry['name']:raise RuntimeError('Unexpected optical import result for '+key)
        asset=objects[0]
        if entry['mesh']:
            if key not in [str(item.material_slot_name) for item in asset.static_materials]:raise RuntimeError('Imported optical material slot differs: '+key)
            nanite=asset.get_editor_property('nanite_settings');nanite.set_editor_property('enabled',False);asset.set_editor_property('nanite_settings',nanite)
        else:
            record=entry['record'];asset.set_editor_property('srgb',record['srgb'])
            normal=key.endswith('Normal')
            compression=unreal.TextureCompressionSettings.TC_NORMALMAP if normal else unreal.TextureCompressionSettings.TC_DEFAULT if record['srgb'] else unreal.TextureCompressionSettings.TC_GRAYSCALE if record['bit_depth']==16 and record['channels']=='R' else unreal.TextureCompressionSettings.TC_MASKS
            asset.set_editor_property('compression_settings',compression);asset.set_editor_property('flip_green_channel',False)
            asset.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP);asset.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
        unreal.EditorAssetLibrary.set_metadata_tag(asset,OWNER,entry['pin']);save(asset);entry['asset']=asset
    generator=unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    materials={};definition_paths={}
    for role,recipe in LOOKS.items():
        name=recipe['name'];definition=definitions[role]
        if not definition:
            factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.CkUsf_LookDefinition)
            definition=tools.create_asset('DA_'+name,ASSET+'/Looks/Optical',unreal.CkUsf_LookDefinition,factory)
            if not definition:raise RuntimeError('Could not create optical look definition '+role)
            params=[_param(parameter,2,entries[key]['asset'].get_path_name(),i*10) for i,(parameter,key) in enumerate(recipe['textures'])]
            params += [_param(key,1,value,i*10) for i,(key,value) in enumerate(recipe['vectors'])]
            params += [_param(key,0,value,i*10) for i,(key,value) in enumerate(recipe['scalars'])]
            for key,value in [('_LookName',name),('_UshIncludePath','/CkUsf/Looks/'+recipe['source']+'.ush'),('_UshFunctionName','CkUsf_Look_'+recipe['source']),('_Parameters',params),('_TwoSided',recipe['two_sided'])]:definition.set_editor_property(key,value)
            for key,value in [('_SurfaceGraph',recipe['graph']),('_Domain',0),('_ShadingModel',recipe['shading']),('_BlendMode',recipe['blend'])]:definition.set_editor_property(key,type(definition.get_editor_property(key)).cast(value))
            unreal.EditorAssetLibrary.set_metadata_tag(definition,OWNER,recipe_pins[role]);save(definition)
        elif role in migrate_roles:
            # Only defaults change. All name, source and topology fields were checked in preflight.
            params=[_param(parameter,2,entries[key]['asset'].get_path_name(),i*10) for i,(parameter,key) in enumerate(recipe['textures'])]
            params += [_param(key,1,value,i*10) for i,(key,value) in enumerate(recipe['vectors'])]
            params += [_param(key,0,value,i*10) for i,(key,value) in enumerate(recipe['scalars'])]
            definition.set_editor_property('_Parameters',params)
            unreal.EditorAssetLibrary.set_metadata_tag(definition,OWNER,recipe_pins[role]);save(definition)
        # Finish native graph generation before the caller starts a separate scene action.
        master_path=ASSET+'/GeneratedLooks/M_CkUsf_Look_'+name;master=unreal.load_asset(master_path)
        if not master or role in migrate_roles:
            generator.generate_look_material_for(definition);master=unreal.load_asset(master_path)
        if not isinstance(master,unreal.Material) or unreal.MaterialEditingLibrary.recompile_material(master):raise RuntimeError('Optical material generation/compile failed: '+role)
        unreal.MaterialEditingLibrary.get_statistics(master);save(master)
        materials[role]=master.get_path_name();definition_paths[role]=definition.get_path_name()
    mesh_paths={role:entries[role]['path'] for role in geometry['meshes']};mesh_paths['Opal']=opal_mesh_path
    report=dict(meshes=mesh_paths,materials=materials,looks=materials,definitions=definition_paths,textures={key:entries[key]['path'] for key in maps},source_hashes=source_hashes,recipe_pins=recipe_pins,migrated_roles=sorted(migrate_roles),ready_for_separate_scene_action=True)
    output=root/'Saved/UsfMaterialGallery/OpticalPair-Preparation.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2))
    return report


