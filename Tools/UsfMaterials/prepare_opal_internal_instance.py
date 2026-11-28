"""Create or verify the separately owned final OpalInternal preset instance."""
from pathlib import Path
import hashlib,json,math
import unreal
from opal_internal_settings import LOOKS

OWNER='CkUsf.OpalInternalInstancePreparation.v1'
PATH='/CkFoundation/CkUsf/Instances/Optical/MI_OpticalOpalInternal'
MASTER='/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_OpticalOpalInternal.M_CkUsf_Look_OpticalOpalInternal'
ROOT=Path(__file__).resolve().parents[2]
PRESET=Path(__file__).with_name('opal_internal_preset.json')
REPORT=ROOT/'Saved/UsfMaterialGallery/OpalInternal-InstancePreparation.json'
# Native reflected names from MaterialInstanceBasePropertyOverrides.h. Using the
# native names avoids ambiguous Python conversion of bOverride_bIsThinSurface.
BASE_OVERRIDE_FLAGS=(
    'bOverride_OpacityMaskClipValue','bOverride_BlendMode','bOverride_ShadingModel',
    'bOverride_DitheredLODTransition','bOverride_CastDynamicShadowAsMasked',
    'bOverride_TwoSided','bOverride_bIsThinSurface','bOverride_OutputTranslucentVelocity',
    'bOverride_bHasPixelAnimation','bOverride_bEnableTessellation','bOverride_DisplacementScaling',
    'bOverride_bEnableDisplacementFade','bOverride_DisplacementFadeRange',
    'bOverride_MaxWorldPositionOffsetDisplacement','bOverride_CompatibleWithLumenCardSharing',
    'bOverride_UsageFlags')


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def context(master):
    if not isinstance(master,unreal.Material) or master.get_path_name()!=MASTER:
        raise RuntimeError('Exact verified Stack3 parent required')
    raw=PRESET.read_bytes()
    preset=json.loads(raw,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    allowed={'schema_version','name','scalars','vectors','sky','environment_intensity','reflection_brightness','body_shadow','front_reflections'}
    if not isinstance(preset,dict) or set(preset)-allowed or type(preset.get('schema_version')) is not int or preset['schema_version']!=1 or not isinstance(preset.get('name'),str):
        raise RuntimeError('Known version1 named preset schema required')
    for field in ['scalars','vectors']:
        values=preset.get(field)
        if not isinstance(values,dict) or set(values)!={'Opal'} or not isinstance(values['Opal'],dict) or set(values['Opal'])-set(dict(LOOKS['Opal'][field])):
            raise RuntimeError('Known Opal material preset parameter roster required')
        for value in values['Opal'].values():
            if not (finite(value) if field=='scalars' else isinstance(value,list) and len(value)==4 and all(finite(v) for v in value)):
                raise RuntimeError('Finite preset scalar/vector values required')
    for field,maximum in [('sky',10),('environment_intensity',1000),('reflection_brightness',100)]:
        if field in preset and (not finite(preset[field]) or not 0<=preset[field]<=maximum):
            raise RuntimeError('Invalid preset lighting field')
    for field in ['body_shadow','front_reflections']:
        if field in preset and not isinstance(preset[field],bool):raise RuntimeError('Boolean preset control required')
    return dict(preset=preset,preset_sha256=hashlib.sha256(raw).hexdigest(),recipe_sha256=hashlib.sha256(json.dumps(preset,sort_keys=True).encode()).hexdigest())


def verify_no_structural_overrides(instance):
    # get_editor_property resolves native reflected names as well as Python names.
    # Missing reflection fails closed instead of accepting an unchecked permutation.
    overrides=instance.get_editor_property('BasePropertyOverrides')
    for name in BASE_OVERRIDE_FLAGS:
        if overrides.get_editor_property(name):
            raise RuntimeError('Preserve unexpected preset base-property override: '+name)
    # StaticParametersRuntime is protected in the Python API. This fixed native
    # master has no material-layer functions; inspect its public switch roster.
    if unreal.MaterialEditingLibrary.get_static_switch_parameter_names(instance):
        raise RuntimeError('Preserve unexpected preset static switch parameters')


def verify(master,instance,claim):
    if not isinstance(instance,unreal.MaterialInstanceConstant) or instance.get_path_name()!=PATH+'.MI_OpticalOpalInternal' or instance.get_editor_property('parent')!=master:
        raise RuntimeError('Preserve missing/foreign instance or changed parent')
    if unreal.EditorAssetLibrary.get_metadata_tag(instance,OWNER)!=claim['recipe_sha256'] or unreal.EditorAssetLibrary.get_metadata_tag(instance,OWNER+'.Preset')!=claim['preset_sha256']:
        raise RuntimeError('Preserve unowned or revised saved preset instance')
    verify_no_structural_overrides(instance)
    library=unreal.MaterialEditingLibrary
    for field,singular in [('scalars','scalar'),('vectors','vector')]:
        overrides=instance.get_editor_property(singular+'_parameter_values')
        names=[str(value.get_editor_property('parameter_info').get_editor_property('name')) for value in overrides]
        expected=claim['preset'][field]['Opal']
        if len(names)!=len(expected) or set(names)!=set(expected):raise RuntimeError('Preserve changed local override roster')
        for key,default in LOOKS['Opal'][field]:
            actual=getattr(library,'get_material_instance_'+singular+'_parameter_value')(instance,key)
            wanted=expected.get(key,default)
            valid=abs(actual-wanted)<1e-5 if field=='scalars' else all(abs(getattr(actual,c)-v)<1e-5 for c,v in zip('rgba',wanted))
            if not valid:raise RuntimeError('Preserve changed effective instance parameter: '+key)
    if instance.get_editor_property('texture_parameter_values') or instance.get_editor_property('double_vector_parameter_values'):
        raise RuntimeError('Preset must inherit textures without additional parameter overrides')
    textures={}
    for key,_ in LOOKS['Opal']['textures']:
        texture=library.get_material_instance_texture_parameter_value(instance,key)
        expected=library.get_material_default_texture_parameter_value(master,key)
        if not texture or texture!=expected:raise RuntimeError('Preserve changed inherited preset texture')
        textures[key]=texture.get_path_name()
    return dict(owner=OWNER,source_instance=instance.get_path_name(),parent=master.get_path_name(),preset_path=PRESET.relative_to(ROOT).as_posix(),
        preset_sha256=claim['preset_sha256'],recipe_sha256=claim['recipe_sha256'],
        scalar_overrides=claim['preset']['scalars']['Opal'],vector_overrides=claim['preset']['vectors']['Opal'],inherited_textures=textures)


def verify_existing(master):
    claim=context(master)
    instance=unreal.load_asset(PATH)
    return instance,verify(master,instance,claim)


def prepare(master):
    claim=context(master)
    exists=unreal.EditorAssetLibrary.does_asset_exist(PATH)
    instance=unreal.load_asset(PATH) if exists else None
    if exists:
        report=verify(master,instance,claim)  # Existing owned instances are never rewritten.
        # A failed validation can leave our complete, owned new object in memory.
        # Save it only after every check passes and only if no asset exists on disk.
        disk=ROOT/'Plugins/CkFoundation/Content/CkUsf/Instances/Optical/MI_OpticalOpalInternal.uasset'
        if not disk.exists() and not unreal.EditorAssetLibrary.save_loaded_asset(instance,only_if_is_dirty=False):
            raise RuntimeError('Could not save verified new owned preset instance')
    else:
        instance=unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_OpticalOpalInternal','/CkFoundation/CkUsf/Instances/Optical',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
        if not isinstance(instance,unreal.MaterialInstanceConstant):raise RuntimeError('Could not create new owned preset instance')
        library=unreal.MaterialEditingLibrary
        library.set_material_instance_parent(instance,master)
        for key,value in claim['preset']['scalars']['Opal'].items():
            # UE 5.8's implementation returns false even after applying the value.
            # Verify effective values below instead of treating that return as status.
            library.set_material_instance_scalar_parameter_value(instance,key,value)
        for key,value in claim['preset']['vectors']['Opal'].items():
            library.set_material_instance_vector_parameter_value(instance,key,unreal.LinearColor(*value))
        unreal.EditorAssetLibrary.set_metadata_tag(instance,OWNER,claim['recipe_sha256'])
        unreal.EditorAssetLibrary.set_metadata_tag(instance,OWNER+'.Preset',claim['preset_sha256'])
        report=verify(master,instance,claim)
        if not unreal.EditorAssetLibrary.save_loaded_asset(instance,only_if_is_dirty=False):raise RuntimeError('Could not save new owned preset instance')
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    temporary=REPORT.with_suffix('.pending')
    temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(REPORT)
    return report
