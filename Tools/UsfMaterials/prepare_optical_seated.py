"""Additive seated-display preparation; reuse pinned textures and untouched depth Opal/Panel."""
from pathlib import Path
import hashlib,json,struct
import unreal
from prepare_native_bsdf import _param
from prepare_optical_depth import _verify_canonical_mesh,_verify_hardware_parameters
OWNER='CkUsf.OpticalSeatedPreparation.v1'
DEPTH_OWNER='CkUsf.OpticalDepthPreparation.v1'
TEXTURE_OWNER='CkUsf.OpticalPairPreparation.v1'
ROLES={'Opal','GlassCover','Panel','Housing','MetalTrim'}
NEW_IDENTITIES={'GlassCover':('OpticalSeatedGlass','OpticalSeatedGlass',6),'Housing':('OpticalSeatedHousing','OpticalSeatedAluminum',0),'MetalTrim':('OpticalSeatedMetalTrim','OpticalSeatedAluminum',0)}
def _sha(data):return hashlib.sha256(data).hexdigest()

def _verify_seated_mesh(path,role,record,geometry):
    if geometry.get('schema_version')!=5 or geometry.get('export_convention')!='CANONICAL_OUTWARD_OBJ_SEATED_MACHINED_V1' or geometry.get('exported_winding_sign')!=1 or geometry.get('vertex_normals_convention')!='Outward independent face-corner normals; glass cap/bevel/wall creases retained, housing/seat planar faces never averaged':raise RuntimeError('Exact V5 outward seated geometry convention required')
    if record['slot']!=role or record['degenerate_triangles']!=0 or not record['closed_edge_manifold'] or not record['consistent_edge_winding']:raise RuntimeError('V5 declared topology differs: '+role)
    # Reuse the proven positive-winding/per-corner-normal topology algorithm after the exact V5 gate.
    contract=dict(geometry,schema_version=4,export_convention='CANONICAL_OUTWARD_OBJ_PER_CORNER_NORMALS_V1')
    result=_verify_canonical_mesh(path,role,record,contract);result['source_variant']='V5_seated_machined';return result

def _verify_definition(definition,path,role,recipe,textures):
    if not isinstance(definition,unreal.CkUsf_LookDefinition) or definition.get_path_name()!=path+'.DA_'+recipe['name']:raise RuntimeError('Preserve definition class/path: '+role)
    for field,expected in [('_LookName',recipe['name']),('_UshIncludePath','/CkUsf/Looks/'+recipe['source']+'.ush'),('_UshFunctionName','CkUsf_Look_'+recipe['source'])]:
        if str(definition.get_editor_property(field))!=expected:raise RuntimeError('Preserve definition identity: '+role+'/'+field)
    if definition.get_editor_property('_TwoSided')!=recipe['two_sided'] or definition.get_editor_property('_DirectionalShading')!=recipe.get('directional_shading',False):raise RuntimeError('Preserve definition shading flags: '+role)
    for field,value in [('_SurfaceGraph',recipe['graph']),('_Domain',0),('_ShadingModel',recipe['shading']),('_BlendMode',recipe['blend'])]:
        actual=definition.get_editor_property(field)
        if actual!=type(actual).cast(value):raise RuntimeError('Preserve definition topology: '+role+'/'+field)
    _verify_hardware_parameters(definition,role,recipe,textures)

def prepare():
    from optical_seated_settings import ASSET,LOOKS
    from optical_depth_settings import LOOKS as DEPTH_LOOKS
    if ASSET!='/CkFoundation/CkUsf' or set(LOOKS)!=ROLES:raise RuntimeError('Exact seated asset root/five roles required')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Prepare seated assets in fresh editor before scene/PIE')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat')!=1:raise RuntimeError('Seated display requires the process-only Adaptive profile')
    root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve();resources=root/'Plugins/CkTests/Resources/CkUsf';source=resources/'OpticalDisplaySeatedV5';source_hashes={}
    def checked(base,relative,pin):
        path=(base/relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(base.resolve()) or not path.is_file() or _sha(path.read_bytes())!=pin:raise RuntimeError('Seated source missing/different: '+str(path))
        source_hashes[str(path.relative_to(root))]=pin;return path
    def receipt(base,name):
        path=base/name;record=json.loads(path.read_text(encoding='utf-8-sig'));checked(root,record['generator_source'],record['generator_sha256']);source_hashes[str(path.relative_to(root))]=_sha(path.read_bytes());return record
    geometry=receipt(source,'Geometry.json');checked(root,geometry['helper_source'],geometry['helper_sha256'])
    if set(geometry['meshes'])!=ROLES-{'Opal'}:raise RuntimeError('V5 must contain four exact display roles')
    checked(root,geometry['canonical_source']['path'],geometry['canonical_source']['sha256'])
    for item in geometry['source_chain']:checked(root,item['path'],item['sha256'])
    textures={}
    for filename in ['DisplayTextures.json','OpalTextures.json']:
        document=receipt(resources/'OpticalPairV1',filename)
        if 'source' in document:checked(resources/'OpticalPairV1',document['source']['path'],document['source']['sha256'])
        for key,info in document['maps'].items():
            if key in textures:raise RuntimeError('Duplicate seated texture key '+key)
            path=checked(resources/'OpticalPairV1',info['path'],info['sha256']);data=path.read_bytes()
            if data[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',data[16:24])!=(info['width'],info['height']) or data[24]!=info['bit_depth']:raise RuntimeError('Seated backing PNG differs: '+key)
            texture=unreal.load_asset(ASSET+'/Textures/Optical/Pair/T_OpticalPair_'+key)
            if not isinstance(texture,unreal.Texture2D) or unreal.EditorAssetLibrary.get_metadata_tag(texture,TEXTURE_OWNER)!=info['sha256']:raise RuntimeError('Preserve missing/revised V1 texture: '+key)
            textures[key]=texture
    v2=receipt(resources/'OpticalDisplayDepthV2','Geometry.json');checked(root,v2['helper_source'],v2['helper_sha256'])
    panel=geometry['meshes']['Panel'];canonical_panel=v2['meshes']['Panel']
    if panel['sha256']!=canonical_panel['sha256'] or panel['mtl']['sha256']!=canonical_panel['mtl']['sha256']:raise RuntimeError('Seated Panel must be byte-identical to preserved V2 source')
    checked(resources/'OpticalDisplayDepthV2',canonical_panel['path'],canonical_panel['sha256']);checked(resources/'OpticalDisplayDepthV2',canonical_panel['mtl']['path'],canonical_panel['mtl']['sha256'])
    amber=receipt(resources/'AmberHeroV1','Manifest.json');body=amber['meshes']['Body'];checked(resources/'AmberHeroV1',body['path'],body['sha256'])
    mesh_paths={'Opal':'/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body','Panel':'/CkTests/CkUsf/Showcase/OpticalDisplayDepth/SM_OpticalDepth_Panel'}
    for role,owner,pin,slot in [('Opal','CkUsf.AmberHeroPreparation.v1',body['sha256'],'Body'),('Panel',DEPTH_OWNER,panel['sha256'],'Panel')]:
        mesh=unreal.load_asset(mesh_paths[role])
        if not isinstance(mesh,unreal.StaticMesh) or slot not in [str(item.material_slot_name) for item in mesh.static_materials] or unreal.EditorAssetLibrary.get_metadata_tag(mesh,owner)!=pin:raise RuntimeError('Preserve missing/revised reused mesh: '+role)
    meshes={};mesh_checks={}
    for role,info in geometry['meshes'].items():
        path=checked(source,info['path'],info['sha256']);checked(source,info['mtl']['path'],info['mtl']['sha256']);mesh_checks[role]=_verify_seated_mesh(path,role,info,geometry)
        if role=='Panel':continue
        name='SM_OpticalSeated_'+role;folder='/CkTests/CkUsf/Showcase/OpticalDisplaySeated';destination=folder+'/'+name;mesh=unreal.load_asset(destination)
        if unreal.EditorAssetLibrary.does_asset_exist(destination) and (not isinstance(mesh,unreal.StaticMesh) or unreal.EditorAssetLibrary.get_metadata_tag(mesh,OWNER)!=info['sha256']):raise RuntimeError('Preserve unknown seated mesh destination: '+role)
        if mesh and role not in [str(item.material_slot_name) for item in mesh.static_materials]:raise RuntimeError('Preserve changed seated mesh slot: '+role)
        meshes[role]=dict(file=path,name=name,folder=folder,path=destination,pin=info['sha256'],asset=mesh);mesh_paths[role]=destination
    definitions={};recipe_pins={};materials={};definition_paths={};existing_masters={}
    for role,recipe in LOOKS.items():
        if role in ['Opal','Panel']:
            if json.dumps(recipe,sort_keys=True)!=json.dumps(DEPTH_LOOKS[role],sort_keys=True):raise RuntimeError('Seated Opal/Panel must reuse exact current depth recipes: '+role)
            owner=DEPTH_OWNER
        else:
            if (recipe['name'],recipe['source'],recipe['graph'])!=NEW_IDENTITIES[role]:raise RuntimeError('Seated material identity differs: '+role)
            owner=OWNER
        if any(key not in textures for _,key in recipe['textures']):raise RuntimeError('Seated recipe texture missing: '+role)
        shader=root/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'/(recipe['source']+'.ush')
        if not shader.is_file() or 'CkUsf_Look_'+recipe['source'] not in shader.read_text():raise RuntimeError('Seated shader entrypoint missing: '+role)
        pin=_sha(json.dumps(recipe,sort_keys=True).encode());recipe_pins[role]=pin;path=ASSET+'/Looks/Optical/DA_'+recipe['name'];definition_paths[role]=path+'.DA_'+recipe['name'];definition=unreal.load_asset(path)
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            if not isinstance(definition,unreal.CkUsf_LookDefinition) or unreal.EditorAssetLibrary.get_metadata_tag(definition,owner)!=pin:raise RuntimeError('Preserve unknown seated/reused definition ownership: '+role)
            _verify_definition(definition,path,role,recipe,textures)
        elif role in ['Opal','Panel']:raise RuntimeError('Persistent depth definition must already exist: '+role)
        definitions[role]=definition
        master_path=ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name'];master=unreal.load_asset(master_path)
        if unreal.EditorAssetLibrary.does_asset_exist(master_path):
            if not isinstance(master,unreal.Material) or not definition or unreal.EditorAssetLibrary.get_metadata_tag(master,'CkUsf.SourceDefinition.v1')!=definition_paths[role]:raise RuntimeError('Preserve unknown seated/reused master: '+role)
            if role not in ['Opal','Panel'] and unreal.EditorAssetLibrary.get_metadata_tag(master,OWNER) not in ['',pin]:raise RuntimeError('Preserve revised seated master recipe tag: '+role)
        elif role in ['Opal','Panel']:raise RuntimeError('Persistent depth master must already exist: '+role)
        existing_masters[role]=master
    # Every source hash, destination owner and reused definition is verified before mutations.
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Could not save seated asset: '+asset.get_path_name())
    for role,entry in meshes.items():
        if entry['asset']:continue
        task=unreal.AssetImportTask();task.filename=str(entry['file']);task.destination_path=entry['folder'];task.destination_name=entry['name'];task.automated=True;task.replace_existing=False;task.save=False
        options=unreal.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=False;data.convert_scene_unit=False;data.import_uniform_scale=1;data.set_editor_property('coordinate_system_policy',unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES);data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.factory=unreal.FbxFactory();task.options=options;tools.import_asset_tasks([task]);objects=task.get_objects()
        if len(objects)!=1 or objects[0].get_path_name()!=entry['path']+'.'+entry['name']:raise RuntimeError('Unexpected seated mesh import: '+role)
        mesh=objects[0]
        if role not in [str(item.material_slot_name) for item in mesh.static_materials]:raise RuntimeError('Seated imported slot mismatch: '+role)
        nanite=mesh.get_editor_property('nanite_settings');nanite.set_editor_property('enabled',False);mesh.set_editor_property('nanite_settings',nanite);unreal.EditorAssetLibrary.set_metadata_tag(mesh,OWNER,entry['pin']);save(mesh)
    generator=unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    for role,recipe in LOOKS.items():
        master=existing_masters[role]
        if role in ['Opal','Panel']:
            # These exact persistent definitions/masters are read-only reuse: no generate, compile or save.
            materials[role]=master.get_path_name();continue
        definition=definitions[role];name=recipe['name']
        if not definition:
            factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.CkUsf_LookDefinition);definition=tools.create_asset('DA_'+name,ASSET+'/Looks/Optical',unreal.CkUsf_LookDefinition,factory)
            if not definition:raise RuntimeError('Could not create seated definition: '+role)
            params=[_param(parameter,2,textures[key].get_path_name(),i*10) for i,(parameter,key) in enumerate(recipe['textures'])]+[_param(key,1,value,i*10) for i,(key,value) in enumerate(recipe['vectors'])]+[_param(key,0,value,i*10) for i,(key,value) in enumerate(recipe['scalars'])]
            for field,value in [('_LookName',name),('_UshIncludePath','/CkUsf/Looks/'+recipe['source']+'.ush'),('_UshFunctionName','CkUsf_Look_'+recipe['source']),('_Parameters',params),('_TwoSided',recipe['two_sided']),('_DirectionalShading',recipe.get('directional_shading',False))]:definition.set_editor_property(field,value)
            for field,value in [('_SurfaceGraph',recipe['graph']),('_Domain',0),('_ShadingModel',recipe['shading']),('_BlendMode',recipe['blend'])]:definition.set_editor_property(field,type(definition.get_editor_property(field)).cast(value))
            unreal.EditorAssetLibrary.set_metadata_tag(definition,OWNER,recipe_pins[role]);save(definition)
        if not master:generator.generate_look_material_for(definition);master=unreal.load_asset(ASSET+'/GeneratedLooks/M_CkUsf_Look_'+name)
        if not isinstance(master,unreal.Material) or unreal.MaterialEditingLibrary.recompile_material(master):raise RuntimeError('Seated material generation/compile failed: '+role)
        unreal.MaterialEditingLibrary.get_statistics(master);unreal.EditorAssetLibrary.set_metadata_tag(master,OWNER,recipe_pins[role]);save(master);materials[role]=master.get_path_name()
    report=dict(source_variant='V5_seated_machined',geometry_source=str(source.relative_to(root)),meshes=mesh_paths,materials=materials,looks=materials,definitions=definition_paths,textures={key:texture.get_path_name() for key,texture in textures.items()},recipe_pins=recipe_pins,source_hashes=source_hashes,mesh_checks=mesh_checks,reused_read_only_roles=['Opal','Panel'],preserved_depth_assets=True,ready_for_separate_scene_action=True)
    output=root/'Saved/UsfMaterialGallery/OpticalSeated-Preparation.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2));return report
