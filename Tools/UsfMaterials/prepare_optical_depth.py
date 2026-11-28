"""Canonical V4 crease-bevel optical depth preparation; V3 is an explicit reversed-winding diagnostic. Never mutate V1 assets or bind a scene."""
from pathlib import Path
from collections import Counter
import copy,hashlib,json,math,struct
import unreal
from prepare_native_bsdf import _param
OWNER='CkUsf.OpticalDepthPreparation.v1'
V1_OWNER='CkUsf.OpticalPairPreparation.v1'
ROLES={'Opal','GlassCover','Panel','Housing','MetalTrim'}
IDENTITIES={'Opal':('OpticalOpalDepth','OpticalOpalDepth',4),'GlassCover':('OpticalDepthGlass','OpticalDepthGlass',6),'Panel':('OpticalDepthPanel','OpticalDisplayPanel',0),'Housing':('OpticalDepthHousing','OpticalDepthHardware',0),'MetalTrim':('OpticalDepthMetalTrim','OpticalDepthHardware',0)}

def _sha(data):return hashlib.sha256(data).hexdigest()

def _verify_mesh(path,role,record,geometry,canonical_path):
    if geometry.get('schema_version')!=3 or geometry.get('export_convention')!='UE_KEEP_XYZ_REVERSED_OBJ_CORNERS_V1' or geometry.get('exported_winding_sign')!=-1 or geometry.get('vertex_normals_convention')!='Unchanged outward canonical source normals; intentionally opposite exported geometric winding':raise RuntimeError('Negative winding is allowed only for the exact V3 Unreal import convention')
    if record.get('source_normals_preserved') is not True or record.get('face_corner_permutation')!=[0,2,1]:raise RuntimeError('V3 requires preserved outward normals and exact reversed corner order: '+role)
    original=canonical_path.read_bytes().decode('ascii').splitlines(keepends=True);exported=path.read_bytes().decode('ascii').splitlines(keepends=True)
    if len(original)!=len(exported):raise RuntimeError('V3 source line count differs: '+role)
    for canonical_line,exported_line in zip(original,exported):
        parts=canonical_line.split()
        if parts and parts[0]=='f':
            if len(parts)!=4 or exported_line.split()!=['f',parts[1],parts[3],parts[2]]:raise RuntimeError('V3 face is not the exact canonical corner permutation: '+role)
        elif exported_line!=canonical_line:raise RuntimeError('V3 changed canonical non-face data: '+role)
    vertices=[];normals=[];faces=[];normal_faces=[];slots=set()
    for line in exported:
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':vertices.append(tuple(float(v) for v in fields[1:4]))
        elif fields[0]=='vn':normals.append(tuple(float(v) for v in fields[1:4]))
        elif fields[0]=='f':
            if len(fields)!=4 or any(len(v.split('/'))!=3 or not v.split('/')[2] for v in fields[1:]):raise RuntimeError('V3 triangle must reference authored normals: '+role)
            faces.append(tuple(int(v.split('/')[0])-1 for v in fields[1:]));normal_faces.append(tuple(int(v.split('/')[2])-1 for v in fields[1:]))
        elif fields[0]=='usemtl':slots.add(fields[1])
    if len(vertices)!=record['vertices'] or len(faces)!=record['triangles'] or slots!={role}:raise RuntimeError('Depth mesh count/slot differs: '+role)
    if not normals or any(not all(math.isfinite(x) for x in n) or abs(sum(x*x for x in n)-1)>1e-4 for n in normals):raise RuntimeError('V3 authored normal must be finite and normalized: '+role)
    edges=Counter();directions=Counter();volume=0;worst_alignment=-1
    for face,normal_face in zip(faces,normal_faces):
        if any(i<0 or i>=len(vertices) for i in face) or any(i<0 or i>=len(normals) for i in normal_face):raise RuntimeError('Depth mesh index invalid: '+role)
        a,b,c=(vertices[i] for i in face);u=tuple(b[i]-a[i] for i in range(3));v=tuple(c[i]-a[i] for i in range(3));cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        area2=sum(x*x for x in cross)
        if not all(math.isfinite(x) for p in (a,b,c) for x in p) or area2<1e-20:raise RuntimeError('Depth mesh nonfinite/degenerate triangle: '+role)
        averaged=tuple(sum(normals[index][axis] for index in normal_face) for axis in range(3));normal2=sum(x*x for x in averaged)
        if normal2<1e-12:raise RuntimeError('V3 averaged authored normal is degenerate: '+role)
        alignment=sum(cross[i]*averaged[i] for i in range(3))/math.sqrt(area2*normal2);worst_alignment=max(worst_alignment,alignment)
        if alignment>=-1e-6:raise RuntimeError('V3 outward authored normal does not oppose reversed exported winding: '+role)
        volume+=sum(a[i]*cross[i] for i in range(3))/6
        for i,j in zip(face,face[1:]+face[:1]):edges[tuple(sorted((i,j)))]+=1;directions[i,j]+=1
    if any(n!=2 for n in edges.values()) or any(directions[a,b]!=directions[b,a] for a,b in edges) or volume>=0:raise RuntimeError('V3 closed reversed topology failed: '+role)
    declared=record['component_signed_volumes_cm3'];canonical_volumes=record['canonical_source']['component_signed_volumes_cm3']
    if len(declared)!=len(canonical_volumes) or not declared or any(a>=0 or b<=0 or not math.isclose(a,-b,rel_tol=1e-6,abs_tol=1e-6) for a,b in zip(declared,canonical_volumes)) or not math.isclose(volume,sum(declared),rel_tol=1e-6,abs_tol=1e-6):raise RuntimeError('V3 exported/canonical signed volumes differ: '+role)
    for axis in range(3):
        if abs(min(p[axis] for p in vertices)-record['bounds']['min'][axis])>1e-6 or abs(max(p[axis] for p in vertices)-record['bounds']['max'][axis])>1e-6:raise RuntimeError('Depth mesh axis/bounds mismatch: '+role)
    return dict(exported_signed_volume_cm3=volume,maximum_normal_winding_alignment=worst_alignment,exact_canonical_corner_reversal=True)
def _verify_canonical_mesh(path,role,record,geometry):
    if geometry.get('axes')!='+X front, +Y width, +Z up':raise RuntimeError('Canonical source axes differ')
    if geometry.get('schema_version')==4:
        if geometry.get('export_convention')!='CANONICAL_OUTWARD_OBJ_PER_CORNER_NORMALS_V1' or geometry.get('exported_winding_sign')!=1:raise RuntimeError('V4 requires canonical outward winding and per-corner normals')
    elif geometry.get('schema_version')!=2:raise RuntimeError('Canonical validation supports only V2 or exact V4 geometry')
    vertices=[];normals=[];faces=[];normal_faces=[];slots=set()
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':vertices.append(tuple(float(v) for v in fields[1:4]))
        elif fields[0]=='vn':normals.append(tuple(float(v) for v in fields[1:4]))
        elif fields[0]=='f':
            if len(fields)!=4 or any(len(v.split('/'))!=3 or not v.split('/')[2] for v in fields[1:]):raise RuntimeError('Canonical OBJ requires authored triangle normals: '+role)
            faces.append(tuple(int(v.split('/')[0])-1 for v in fields[1:]));normal_faces.append(tuple(int(v.split('/')[2])-1 for v in fields[1:]))
        elif fields[0]=='usemtl':slots.add(fields[1])
    if len(vertices)!=record['vertices'] or len(faces)!=record['triangles'] or slots!={role}:raise RuntimeError('Canonical mesh count/slot differs: '+role)
    if not normals or any(not all(math.isfinite(x) for x in n) or abs(sum(x*x for x in n)-1)>1e-4 for n in normals):raise RuntimeError('Canonical authored normals must be finite/normalized: '+role)
    edges=Counter();directions=Counter();volume=0;minimum_alignment=1
    for face,normal_face in zip(faces,normal_faces):
        if any(i<0 or i>=len(vertices) for i in face) or any(i<0 or i>=len(normals) for i in normal_face):raise RuntimeError('Canonical mesh index invalid: '+role)
        a,b,c=(vertices[i] for i in face);u=tuple(b[i]-a[i] for i in range(3));v=tuple(c[i]-a[i] for i in range(3));cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);area2=sum(x*x for x in cross)
        if not all(math.isfinite(x) for p in (a,b,c) for x in p) or area2<1e-20:raise RuntimeError('Canonical mesh nonfinite/degenerate triangle: '+role)
        averaged=tuple(sum(normals[index][axis] for index in normal_face) for axis in range(3));normal2=sum(x*x for x in averaged)
        if normal2<1e-12:raise RuntimeError('Canonical averaged authored normal invalid: '+role)
        alignment=sum(cross[i]*averaged[i] for i in range(3))/math.sqrt(area2*normal2);minimum_alignment=min(minimum_alignment,alignment)
        if alignment<=1e-6:raise RuntimeError('Canonical authored normal does not align with source winding: '+role)
        volume+=sum(a[i]*cross[i] for i in range(3))/6
        for i,j in zip(face,face[1:]+face[:1]):edges[tuple(sorted((i,j)))]+=1;directions[i,j]+=1
    declared=record['component_signed_volumes_cm3']
    if any(n!=2 for n in edges.values()) or any(directions[a,b]!=directions[b,a] for a,b in edges) or volume<=0 or not declared or any(value<=0 for value in declared) or not math.isclose(volume,sum(declared),rel_tol=1e-6,abs_tol=1e-6):raise RuntimeError('Canonical closed positive topology/volume failed: '+role)
    for axis in range(3):
        if abs(min(p[axis] for p in vertices)-record['bounds']['min'][axis])>1e-6 or abs(max(p[axis] for p in vertices)-record['bounds']['max'][axis])>1e-6:raise RuntimeError('Canonical mesh axis/bounds mismatch: '+role)
    return dict(source_variant='V4_canonical_crease_bevel' if geometry['schema_version']==4 else 'V2_canonical',exported_signed_volume_cm3=volume,minimum_normal_winding_alignment=minimum_alignment,normal_indexing='independent per-face-corner OBJ indices')
def _verify_hardware_parameters(definition,role,recipe,textures):
    expected=[_param(parameter,2,textures[key].get_path_name(),i*10) for i,(parameter,key) in enumerate(recipe['textures'])]+[_param(key,1,value,i*10) for i,(key,value) in enumerate(recipe['vectors'])]+[_param(key,0,value,i*10) for i,(key,value) in enumerate(recipe['scalars'])]
    actual=list(definition.get_editor_property('_Parameters'))
    if len(actual)!=len(expected):raise RuntimeError('Preserve changed depth hardware parameter count: '+role)
    for index,(current,original) in enumerate(zip(actual,expected)):
        label=role+'/'+str(original.get_editor_property('_Name'))+' index '+str(index)
        for field in ['_Name','_Type','_Group','_SortPriority','_DefaultTexturePath','_PerInstance','_PerInstanceSlot','_CustomPrimitiveData','_CustomPrimitiveDataIndex']:
            if current.get_editor_property(field)!=original.get_editor_property(field):raise RuntimeError('Preserve changed hardware parameter '+label+'/'+field)
        if not math.isclose(current.get_editor_property('_DefaultScalar'),original.get_editor_property('_DefaultScalar'),rel_tol=0,abs_tol=1e-6):raise RuntimeError('Preserve changed hardware scalar '+label)
        a=current.get_editor_property('_DefaultVector');b=original.get_editor_property('_DefaultVector')
        if any(not math.isclose(getattr(a,c),getattr(b,c),rel_tol=0,abs_tol=1e-6) for c in 'rgba'):raise RuntimeError('Preserve changed hardware vector '+label)
DEFAULT_REFINEMENTS={'Panel':('EmissionStrength',32,130),'GlassCover':('EdgePathCm',6,9),'Opal':('WavelengthShift',0,.22)}

def _initial_refinement_recipe(role,recipe,initial):
    parameter,before,after=DEFAULT_REFINEMENTS[role]
    current_values=[value for key,value in recipe['scalars'] if key==parameter]
    initial_values=[value for key,value in initial['scalars'] if key==parameter]
    if len(current_values)!=1 or len(initial_values)!=1 or not math.isclose(current_values[0],after,rel_tol=0,abs_tol=1e-12) or not math.isclose(initial_values[0],before,rel_tol=0,abs_tol=1e-12):raise RuntimeError('Depth default refinement exceeds its exact authorized scalar change: '+role)
    reconstructed=copy.deepcopy(recipe)
    reconstructed['scalars']=[(key,before if key==parameter else value) for key,value in reconstructed['scalars']]
    if _sha(json.dumps(reconstructed,sort_keys=True).encode())!=_sha(json.dumps(initial,sort_keys=True).encode()):raise RuntimeError('Depth refinement changed fields outside the authorized default: '+role)
    return initial

def prepare(reversed_diagnostic=False):
    from optical_depth_settings import ASSET,LOOKS,INITIAL_LOOKS
    if not isinstance(reversed_diagnostic,bool):raise RuntimeError('reversed_diagnostic must be an explicit boolean')
    if ASSET!='/CkFoundation/CkUsf' or set(LOOKS)!=ROLES or set(INITIAL_LOOKS)!=ROLES:raise RuntimeError('Exact optical depth asset root/roles required')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Prepare optical depth in fresh editor outside PIE and before dirty scene creation')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat')!=1:raise RuntimeError('Optical depth requires Adaptive profile')
    root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve();v1=root/'Plugins/CkTests/Resources/CkUsf/OpticalPairV1';source=root/'Plugins/CkTests/Resources/CkUsf'/('OpticalDisplayDepthV3' if reversed_diagnostic else 'OpticalDisplayDepthV4')
    source_hashes={}
    def checked(base,relative,pin):
        path=(base/relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(base.resolve()) or not path.is_file() or _sha(path.read_bytes())!=pin:raise RuntimeError('Preserve missing/different depth source: '+str(path))
        source_hashes[str(path.relative_to(root))]=pin;return path
    def receipt(base,name):
        path=base/name;record=json.loads(path.read_text(encoding='utf-8-sig'));checked(root,record['generator_source'],record['generator_sha256']);source_hashes[str(path.relative_to(root))]=_sha(path.read_bytes());return record
    geometry=receipt(source,'Geometry.json');checked(root,geometry['helper_source'],geometry['helper_sha256'])
    if set(geometry['meshes'])!=ROLES-{'Opal'}:raise RuntimeError('Exact four display mesh roles required')
    if reversed_diagnostic:
        if geometry.get('schema_version')!=3 or geometry.get('export_convention')!='UE_KEEP_XYZ_REVERSED_OBJ_CORNERS_V1' or geometry.get('exported_winding_sign')!=-1:raise RuntimeError('Explicit reversed diagnostic requires exact V3 convention')
        checked(root,geometry['canonical_source']['path'],geometry['canonical_source']['sha256'])
        for item in geometry['source_chain']:checked(root,item['path'],item['sha256'])
    else:
        if geometry.get('schema_version')!=4 or geometry.get('export_convention')!='CANONICAL_OUTWARD_OBJ_PER_CORNER_NORMALS_V1' or geometry.get('exported_winding_sign')!=1:raise RuntimeError('Default preparation requires canonical V4 crease-bevel geometry')
        canonical_receipt=root/'Plugins/CkTests/Resources/CkUsf/OpticalDisplayDepthV2'
        canonical_geometry=receipt(canonical_receipt,'Geometry.json');checked(root,canonical_geometry['helper_source'],canonical_geometry['helper_sha256'])
        if 'canonical_source' in geometry:checked(root,geometry['canonical_source']['path'],geometry['canonical_source']['sha256'])
        for item in geometry.get('source_chain',[]):checked(root,item['path'],item['sha256'])
    maps={};textures={}
    for name in ['DisplayTextures.json','OpalTextures.json']:
        record=receipt(v1,name)
        if 'source' in record:checked(v1,record['source']['path'],record['source']['sha256'])
        for key,info in record['maps'].items():
            if key in maps:raise RuntimeError('Duplicate V1 depth texture key: '+key)
            path=checked(v1,info['path'],info['sha256']);data=path.read_bytes()
            if data[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',data[16:24])!=(info['width'],info['height']) or data[24]!=info['bit_depth']:raise RuntimeError('V1 texture container mismatch: '+key)
            texture_path=ASSET+'/Textures/Optical/Pair/T_OpticalPair_'+key;texture=unreal.load_asset(texture_path)
            if not isinstance(texture,unreal.Texture2D) or unreal.EditorAssetLibrary.get_metadata_tag(texture,V1_OWNER)!=info['sha256']:raise RuntimeError('Preserve missing/differently owned V1 texture: '+key)
            maps[key]=info;textures[key]=texture
    amber=root/'Plugins/CkTests/Resources/CkUsf/AmberHeroV1';amber_manifest=receipt(amber,'Manifest.json');body=amber_manifest['meshes']['Body'];checked(amber,body['path'],body['sha256'])
    opal_path='/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body';opal=unreal.load_asset(opal_path)
    if not isinstance(opal,unreal.StaticMesh) or 'Body' not in [str(m.material_slot_name) for m in opal.static_materials] or unreal.EditorAssetLibrary.get_metadata_tag(opal,'CkUsf.AmberHeroPreparation.v1')!=body['sha256']:raise RuntimeError('Preserve missing/revised reused AmberHero body')
    def owned(path,cls,pin):
        obj=unreal.load_asset(path)
        if unreal.EditorAssetLibrary.does_asset_exist(path) and (not isinstance(obj,cls) or unreal.EditorAssetLibrary.get_metadata_tag(obj,OWNER)!=pin):raise RuntimeError('Preserve unknown existing depth destination: '+path)
        return obj
    def save(obj):
        if not unreal.EditorAssetLibrary.save_loaded_asset(obj,only_if_is_dirty=False):raise RuntimeError('Could not save depth asset '+obj.get_path_name())
    meshes={};definitions={};pins={};migrate_roles=set();refine_roles=set();mesh_checks={};initial_refinement_pins={}
    for role,info in geometry['meshes'].items():
        path=checked(source,info['path'],info['sha256']);checked(source,info['mtl']['path'],info['mtl']['sha256'])
        if info['slot']!=role or info['degenerate_triangles']!=0 or not info['closed_edge_manifold'] or not info['consistent_edge_winding']:raise RuntimeError('Declared depth mesh topology failed: '+role)
        if reversed_diagnostic:
            canonical_path=checked(root,info['canonical_source']['path'],info['canonical_source']['sha256'])
            mesh_checks[role]=_verify_mesh(path,role,info,geometry,canonical_path)
        else:
            if role!='GlassCover':
                canonical=canonical_geometry['meshes'][role]
                if info['sha256']!=canonical['sha256'] or info['mtl']['sha256']!=canonical['mtl']['sha256']:raise RuntimeError('V4 non-glass mesh must remain byte-identical to preserved V2 source: '+role)
                checked(canonical_receipt,canonical['path'],canonical['sha256']);checked(canonical_receipt,canonical['mtl']['path'],canonical['mtl']['sha256'])
            mesh_checks[role]=_verify_canonical_mesh(path,role,info,geometry)
        prefix='SM_OpticalDepthFront_' if reversed_diagnostic else 'SM_OpticalDepthBevel_' if role=='GlassCover' else 'SM_OpticalDepth_'
        name=prefix+role;folder='/CkTests/CkUsf/Showcase/OpticalDisplayDepth';destination=folder+'/'+name
        meshes[role]=dict(file=path,name=name,folder=folder,path=destination,pin=info['sha256'],asset=owned(destination,unreal.StaticMesh,info['sha256']))
    for role,recipe in LOOKS.items():
        if (recipe['name'],recipe['source'],recipe['graph'])!=IDENTITIES[role]:raise RuntimeError('Depth material identity differs: '+role)
        if any(key not in textures for _,key in recipe['textures']):raise RuntimeError('Depth recipe references missing V1 texture: '+role)
        shader=root/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'/(recipe['source']+'.ush')
        if not shader.is_file() or 'CkUsf_Look_'+recipe['source'] not in shader.read_text():raise RuntimeError('Depth shader entrypoint missing: '+role)
        pin=_sha(json.dumps(recipe,sort_keys=True).encode());pins[role]=pin;path=ASSET+'/Looks/Optical/DA_'+recipe['name']
        if role in ['Housing','MetalTrim']:
            if recipe.get('directional_shading') is not True:raise RuntimeError('Corrected depth hardware requires explicit directional_shading=True')
            initial=copy.deepcopy(recipe);initial['graph']=1;initial.pop('directional_shading')
            initial_pin=_sha(json.dumps(initial,sort_keys=True).encode())
            definition=unreal.load_asset(path)
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                if not isinstance(definition,unreal.CkUsf_LookDefinition) or definition.get_path_name()!=path+'.DA_'+recipe['name']:raise RuntimeError('Preserve unknown hardware definition class/path: '+role)
                actual_pin=unreal.EditorAssetLibrary.get_metadata_tag(definition,OWNER)
                if actual_pin not in {pin,initial_pin}:raise RuntimeError('Preserve unknown hardware recipe ownership: '+role)
                for field,expected in [('_LookName',recipe['name']),('_UshIncludePath','/CkUsf/Looks/'+recipe['source']+'.ush'),('_UshFunctionName','CkUsf_Look_'+recipe['source'])]:
                    if str(definition.get_editor_property(field))!=expected:raise RuntimeError('Preserve changed hardware identity: '+role+'/'+field)
                if definition.get_editor_property('_TwoSided')!=recipe['two_sided']:raise RuntimeError('Preserve changed hardware sidedness: '+role)
                for field,value in [('_Domain',0),('_ShadingModel',recipe['shading']),('_BlendMode',recipe['blend']),('_SurfaceGraph',1 if actual_pin==initial_pin else 0)]:
                    actual=definition.get_editor_property(field)
                    if actual!=type(actual).cast(value):raise RuntimeError('Preserve changed hardware topology: '+role+'/'+field)
                if definition.get_editor_property('_DirectionalShading')!=(actual_pin==pin):raise RuntimeError('Preserve changed hardware directional shading: '+role)
                _verify_hardware_parameters(definition,role,recipe,textures)
                if actual_pin==initial_pin:migrate_roles.add(role)
            definitions[role]=definition
        elif role in DEFAULT_REFINEMENTS:
            initial=_initial_refinement_recipe(role,recipe,INITIAL_LOOKS[role]);initial_pin=_sha(json.dumps(initial,sort_keys=True).encode());initial_refinement_pins[role]=initial_pin
            definition=unreal.load_asset(path)
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                if not isinstance(definition,unreal.CkUsf_LookDefinition) or definition.get_path_name()!=path+'.DA_'+recipe['name']:raise RuntimeError('Preserve unknown depth refinement class/path: '+role)
                actual_pin=unreal.EditorAssetLibrary.get_metadata_tag(definition,OWNER)
                if actual_pin not in {pin,initial_pin}:raise RuntimeError('Preserve unknown depth refinement recipe ownership: '+role)
                for field,expected in [('_LookName',recipe['name']),('_UshIncludePath','/CkUsf/Looks/'+recipe['source']+'.ush'),('_UshFunctionName','CkUsf_Look_'+recipe['source'])]:
                    if str(definition.get_editor_property(field))!=expected:raise RuntimeError('Preserve changed depth refinement identity: '+role+'/'+field)
                if definition.get_editor_property('_TwoSided')!=recipe['two_sided'] or definition.get_editor_property('_DirectionalShading')!=recipe.get('directional_shading',False):raise RuntimeError('Preserve changed depth refinement shading flags: '+role)
                for field,value in [('_Domain',0),('_ShadingModel',recipe['shading']),('_BlendMode',recipe['blend']),('_SurfaceGraph',recipe['graph'])]:
                    actual=definition.get_editor_property(field)
                    if actual!=type(actual).cast(value):raise RuntimeError('Preserve changed depth refinement topology: '+role+'/'+field)
                _verify_hardware_parameters(definition,role,initial if actual_pin==initial_pin else recipe,textures)
                if actual_pin==initial_pin:refine_roles.add(role)
            definitions[role]=definition
        else:definitions[role]=owned(path,unreal.CkUsf_LookDefinition,pin)
        master_path=ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name'];master=unreal.load_asset(master_path)
        if unreal.EditorAssetLibrary.does_asset_exist(master_path) and (not isinstance(master,unreal.Material) or unreal.EditorAssetLibrary.get_metadata_tag(master,'CkUsf.SourceDefinition.v1')!=path+'.DA_'+recipe['name']):raise RuntimeError('Preserve unknown depth master: '+master_path)
    # Entire source/destination batch has passed; mesh mutations are confined to the explicitly selected owned asset namespace.
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    for role,entry in meshes.items():
        if entry['asset']:continue
        task=unreal.AssetImportTask();task.filename=str(entry['file']);task.destination_path=entry['folder'];task.destination_name=entry['name'];task.automated=True;task.replace_existing=False;task.save=False
        options=unreal.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=False;data.convert_scene_unit=False;data.import_uniform_scale=1;data.set_editor_property('coordinate_system_policy',unreal.CoordinateSystemPolicy.KEEP_XYZ_AXES);data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.factory=unreal.FbxFactory();task.options=options;tools.import_asset_tasks([task]);objects=task.get_objects()
        if len(objects)!=1 or objects[0].get_path_name()!=entry['path']+'.'+entry['name']:raise RuntimeError('Depth import destination differs: '+role)
        mesh=objects[0]
        if role not in [str(m.material_slot_name) for m in mesh.static_materials]:raise RuntimeError('Depth imported slot differs: '+role)
        nanite=mesh.get_editor_property('nanite_settings');nanite.set_editor_property('enabled',False);mesh.set_editor_property('nanite_settings',nanite);unreal.EditorAssetLibrary.set_metadata_tag(mesh,OWNER,entry['pin']);save(mesh);entry['asset']=mesh
    generator=unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem);materials={};definition_paths={}
    for role,recipe in LOOKS.items():
        definition=definitions[role];name=recipe['name']
        if not definition:
            factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.CkUsf_LookDefinition);definition=tools.create_asset('DA_'+name,ASSET+'/Looks/Optical',unreal.CkUsf_LookDefinition,factory)
            if not definition:raise RuntimeError('Could not create additive depth look '+role)
            params=[_param(parameter,2,textures[key].get_path_name(),i*10) for i,(parameter,key) in enumerate(recipe['textures'])]+[_param(key,1,value,i*10) for i,(key,value) in enumerate(recipe['vectors'])]+[_param(key,0,value,i*10) for i,(key,value) in enumerate(recipe['scalars'])]
            for field,value in [('_LookName',name),('_UshIncludePath','/CkUsf/Looks/'+recipe['source']+'.ush'),('_UshFunctionName','CkUsf_Look_'+recipe['source']),('_Parameters',params),('_TwoSided',recipe['two_sided']),('_DirectionalShading',recipe.get('directional_shading',False))]:definition.set_editor_property(field,value)
            for field,value in [('_SurfaceGraph',recipe['graph']),('_Domain',0),('_ShadingModel',recipe['shading']),('_BlendMode',recipe['blend'])]:definition.set_editor_property(field,type(definition.get_editor_property(field)).cast(value))
            unreal.EditorAssetLibrary.set_metadata_tag(definition,OWNER,pins[role]);save(definition)
        elif role in migrate_roles:
            definition.set_editor_property('_SurfaceGraph',type(definition.get_editor_property('_SurfaceGraph')).cast(0))
            definition.set_editor_property('_DirectionalShading',True)
            unreal.EditorAssetLibrary.set_metadata_tag(definition,OWNER,pins[role]);save(definition)
        elif role in refine_roles:
            # The existing full roster was verified against its exact initial recipe before any import.
            params=[_param(parameter,2,textures[key].get_path_name(),i*10) for i,(parameter,key) in enumerate(recipe['textures'])]+[_param(key,1,value,i*10) for i,(key,value) in enumerate(recipe['vectors'])]+[_param(key,0,value,i*10) for i,(key,value) in enumerate(recipe['scalars'])]
            definition.set_editor_property('_Parameters',params)
            unreal.EditorAssetLibrary.set_metadata_tag(definition,OWNER,pins[role]);save(definition)
        path=ASSET+'/GeneratedLooks/M_CkUsf_Look_'+name;master=unreal.load_asset(path)
        generated=not master or role in migrate_roles or role in refine_roles
        if generated:generator.generate_look_material_for(definition);master=unreal.load_asset(path)
        if not isinstance(master,unreal.Material) or unreal.MaterialEditingLibrary.recompile_material(master):raise RuntimeError('Depth master generation/compile failed: '+role)
        unreal.MaterialEditingLibrary.get_statistics(master)
        if generated:save(master)
        materials[role]=master.get_path_name();definition_paths[role]=definition.get_path_name()
    mesh_paths={role:entry['path'] for role,entry in meshes.items()};mesh_paths['Opal']=opal_path
    report=dict(source_variant="V3_reversed_diagnostic" if reversed_diagnostic else "V4_canonical_crease_bevel",reversed_diagnostic=reversed_diagnostic,geometry_source=str(source.relative_to(root)),meshes=mesh_paths,materials=materials,looks=materials,definitions=definition_paths,textures={key:obj.get_path_name() for key,obj in textures.items()},recipe_pins=pins,mesh_checks=mesh_checks,migrated_roles=sorted(migrate_roles|refine_roles),refined_default_roles=sorted(refine_roles),initial_refinement_pins=initial_refinement_pins,source_hashes=source_hashes,preserved_v1_textures=True,ready_for_separate_scene_action=True)
    output=root/'Saved/UsfMaterialGallery/OpticalDepth-Preparation.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2));return report







