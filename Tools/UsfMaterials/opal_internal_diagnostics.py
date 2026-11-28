"""Fixed owned-session material diagnostics. Importing performs no work."""
import os
import uuid
import unreal

MASTERS={
    'stack3':'/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_OpticalOpalInternal',
    'layered2':'/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_OpticalOpalLayeredFire',
}
PROPERTIES=['translucency_lighting_mode','fully_rough','is_thin_surface',
    'tangent_space_normal','blend_mode','refraction_method','normal_curvature_to_roughness']
STATS=['valid','closure_count','uint_per_pixel','has_glint','complex_special',
    'material_type','bsdf_features','compile_errors']
DUMP_STACK3 = False


def material(role):
    path=MASTERS[role]
    master=unreal.load_asset(path)
    if not isinstance(master,unreal.Material) or master.get_path_name()!=path+'.'+path.rsplit('/',1)[1]:
        raise RuntimeError('Exact existing diagnostic master missing: '+path)
    return master


def readback(master):
    values={key:master.get_editor_property(key) for key in PROPERTIES}
    for key in ['translucency_lighting_mode','blend_mode','refraction_method']:
        values[key]=str(values[key])
    stats=unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem).get_compiled_substrate_stats(master)
    front=unreal.MaterialEditingLibrary.get_material_property_input_node(master,unreal.MaterialProperty.MP_FRONT_MATERIAL)
    return dict(master=master.get_path_name(),render_properties=values,
        compiled={key:list(getattr(stats,key)) if key=='compile_errors' else getattr(stats,key) for key in STATS},
        front=front.get_path_name() if front else None,
        front_class=front.get_class().get_path_name() if front else None)


def cvars():
    result={}
    for name in ['r.Roughness.Min','r.Roughness.Max','ShowFlag.Specular','ShowFlag.Lighting','ShowFlag.ReflectionEnvironment','r.Substrate.Debug.PeelLayersAboveDepth']:
        raw=unreal.SystemLibrary.get_console_variable_string_value(name)
        if raw=='':
            result[name]=dict(known=False,value=None)
        else:
            getter=(unreal.SystemLibrary.get_console_variable_float_value if name.startswith('r.Roughness.') else unreal.SystemLibrary.get_console_variable_int_value)
            result[name]=dict(known=True,value=getter(name))
    result['r.Shadow.Virtual.Enable']=dict(known=True,value=unreal.SystemLibrary.get_console_variable_int_value('r.Shadow.Virtual.Enable'))
    return result


def run(request):
    session=os.environ.get('CK_OPAL_INTERNAL_SESSION_ID','')
    if str(uuid.UUID(session))!=session or request.get('session_id')!=session or str(uuid.UUID(request.get('id','')))!=request.get('id') or request.get('action')!='diagnostics':
        raise RuntimeError('Owned diagnostic session/request identity required')
    op=request.get('op')
    allowed={'id','session_id','action','op'}|({'value'} if op=='shadow_mode' else set())
    if op not in ['inspect','compile_comparison','shadow_mode'] or set(request)-allowed:
        raise RuntimeError('Unsupported fixed diagnostic operation/fields')
    if op=='shadow_mode' and (type(request.get('value')) is not int or request['value'] not in [0,1]):
        raise RuntimeError('Only integer shadow_mode0 or1 is permitted')
    # Resolve both exact persistent objects before any explicit compile/CVar mutation.
    masters={role:material(role) for role in MASTERS}
    result=dict(op=op,session_id=session,pid=os.getpid(),before={role:readback(master) for role,master in masters.items()})
    if op=='inspect':
        # Existing resource completion only: no PostEditChange/forced recompile.
        # Engine GetStatistics may submit missing jobs for this current shader map.
        unreal.MaterialEditingLibrary.get_statistics(masters['stack3'])
        result['completion_barrier']=dict(used=True,master=masters['stack3'].get_path_name(),
            api='MaterialEditingLibrary.get_statistics',forced_recompile=False,
            existing_resource_completion=True)
    elif op=='compile_comparison':
        # Compile both fixed comparison participants, including existing child MIDs.
        # This distinguishes a stale render resource from a graph/shading defect.
        # Dump source only. Warm job-cache validation is deliberately forbidden:
        # UE's existing cache entries do not necessarily have diagnostic job names.
        if unreal.SystemLibrary.get_console_variable_int_value('r.ShaderCompiler.DebugValidateJobCache')!=0:
            raise RuntimeError('Disable shader job-cache validation before this diagnostic')
        names=['r.DumpShaderDebugInfo','r.DumpShaderDebugShortNames','r.ShaderCompiler.DumpDebugInfoForCacheHits'] if DUMP_STACK3 else []
        saved={name:unreal.SystemLibrary.get_console_variable_int_value(name) for name in names}
        selected=[masters['stack3']] if DUMP_STACK3 else list(masters.values())
        try:
            for name in names:unreal.SystemLibrary.execute_console_command(None,name+' 1')
            for master in selected:
                unreal.MaterialEditingLibrary.recompile_material(master)
                unreal.MaterialEditingLibrary.get_statistics(master)
        finally:
            for name,value in saved.items():unreal.SystemLibrary.execute_console_command(None,name+' '+str(value))
        result['explicitly_recompiled']=[master.get_path_name() for master in selected]
        result['dump_cvars_before']=saved
        result['dump_cvars_restored']={name:unreal.SystemLibrary.get_console_variable_int_value(name) for name in names}
    elif op=='shadow_mode':
        before=unreal.SystemLibrary.get_console_variable_int_value('r.Shadow.Virtual.Enable')
        # No arbitrary command text: this one fixed CVar and validated integer only.
        unreal.SystemLibrary.execute_console_command(None,'r.Shadow.Virtual.Enable '+str(request['value']))
        after=unreal.SystemLibrary.get_console_variable_int_value('r.Shadow.Virtual.Enable')
        result['shadow_mode']=dict(before=before,requested=request['value'],after=after,applied=after==request['value'])
    result.update(after={role:readback(master) for role,master in masters.items()},cvars=cvars(),
        limitations=['ShowFlag values are console overrides, not a sampled effective viewport show-flag state.',
            'No material save, asset generation, actor assignment or launch performed.'])
    return result
