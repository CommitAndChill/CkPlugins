"""Serial same-object native proof of the three new diorama POM/WPO pairs."""
import hashlib
import json
from pathlib import Path
from verify_industrial_reload import command, wait_reload, OUTPUT, SHADERS, LOG
from verify_river_pebbles import pixels, metric, arguments
from diorama_settings import presentation

ROOT=Path(__file__).resolve().parents[2]
PATCHES=['grass','dirt','mud']
VIEWS={'Oblique':(65,45),'Low':(70,17),'Top':(5,70),'Control':(65,25)}
IDENTITY=['actor','mid','parent','mesh','textures','scale','colors','rect_intensities']


def require(value,message):
    if not value: raise RuntimeError(message)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def run_patch(patch):
    manifest_path=ROOT/'Plugins/CkTests/Resources/CkUsf/DioramaPatchesV1/Manifest.json'
    manifest=json.loads(manifest_path.read_text());record=manifest['materials'][patch]
    look=record['look_id'];source=SHADERS/('Looks/'+look+'.ush')
    original=source.read_bytes();owned=original
    pom,wpo=patch+'_pom',patch+'_displacement'
    initial=command('state')
    report={'passed':False,'restored':False,'patch':patch,'initial_state':initial,'captures':{},'metrics':{},
            'reloads':[],'source_sha256':sha(source),'manifest_sha256':sha(manifest_path),
            'preparation_sha256':sha(OUTPUT/'DioramaPreparation.json')}
    expected_keys={'pom','displacement'}|{p+'_'+mode for p in PATCHES for mode in ['pom','displacement']}
    require(set(initial['environment'])==expected_keys and len(initial['library'])==42,'Missing environment/library roster')
    require(not initial['inspection_orbit']['enabled'] and initial['inspection_orbit']['intensity']==0
            and not initial['preview_quality'] and initial['diagnostic_light'] is None,'Restore temporary lighting/quality before proof')
    require(json.loads((OUTPUT/'DioramaPreparation.json').read_text())['manifest_sha256']==sha(manifest_path),'Stale preparation')
    expected_bindings={c+'Map':'/CkFoundation/CkUsf/Textures/Environment/'+v['runtime_name']+'.'+v['runtime_name'] for c,v in record['maps'].items()}
    for key,displaced in [(pom,False),(wpo,True)]:
        state=initial['environment'][key];values=state['values']
        require(state['textures']==expected_bindings and state['parent'].endswith('M_CkUsf_Look_'+look+'.M_CkUsf_Look_'+look)
                and values['PomAmount']==(0 if displaced else 1) and values['DisplacementAmount']==(1 if displaced else 0)
                and abs(values['ReliefCm']-presentation(record)['ReliefCm'])<1e-5 and values['UVScale']==1
                and values['NormalStrength']==1 and values['StepCount']==64 and values['DebugView']==0
                and values['TileSizeCm']==80 and values['HeightMip']==presentation(record)['HeightMip'] and state['scale']==[1,1,1], 'Wrong diorama bindings/defaults')
    expected_values={key:dict(value['values']) for key,value in initial['environment'].items()}

    def capture(label,station,values=None,view='Oblique'):
        args=[]
        for key,value in (values or {}).items(): args+=['--scalar',key+'='+str(value)]
        distance,height=VIEWS[view];filename='Diorama-'+patch+'-'+label+'.png'
        result=command('capture','--environment',station,'--name',filename,'--shot','--distance',distance,'--height',height,*args)['state']
        expected_values[station].update(values or {})
        require(result['pid']==initial['pid'] and result['library']==initial['library'],'Library/editor changed')
        require(result['inspection_orbit']==initial['inspection_orbit'],'Inspection light changed')
        for key,before in initial['environment'].items():
            now=result['environment'][key]
            require(all(now[f]==before[f] for f in IDENTITY) and now['same_mid'] and now['same_master'],'Environment identity changed: '+key)
            require(now['values']==expected_values[key],'Scalar override missing or unexpected value: '+key)
        taa=label.startswith('TAA-')
        require(result['render_cvars']['r.AntiAliasingMethod']==(2 if taa else 0)
                and result['render_cvars']['r.ScreenPercentage']==(100 if taa else 87),'Native/TAA quality differs')
        report['captures'][label]={'image':filename,'sha256':sha(OUTPUT/filename),'state':result}
        print(patch+' capture '+label,flush=True)
        return pixels(filename)

    def mutate(data):
        nonlocal owned
        require(source.read_bytes()==owned,'Concurrent source edit; preserve it and stop')
        offset=LOG.stat().st_size;owned=data;source.write_bytes(data)
        report['reloads'].append(wait_reload(offset))

    def measured(name,a,b):
        report['metrics'][name]=metric(a,b)
        return report['metrics'][name]['mean_absolute_rgb']

    def response(name,a,b,minimum,noise):
        effect=measured(name,a,b);threshold=max(minimum,3*noise)
        report['metrics'][name]['required_mean_above_repeat_noise']=threshold
        require(effect>threshold,'Rendered response below repeat noise: '+name)
        return effect

    try:
        command('environment_proof_begin')
        for taa in [False,True]:
            if taa: command('preview_quality')
            try:
                for station,mode in [(pom,'pom'),(wpo,'displacement')]:
                    for view in ['Oblique','Low','Top']: capture(('TAA' if taa else 'Native')+'-'+mode+'-'+view,station,view=view)
            finally:
                if taa: command('restore_quality')
        for debug,name in [(1,'BaseColor'),(2,'Normal'),(3,'Roughness'),(5,'Height')]:capture('Inspect-'+name,pom,{'DebugView':debug})
        a=capture('POM-Off-UV',pom,{'DebugView':8,'PomAmount':0},'Control')
        b=capture('POM-Off-UV-Repeat',pom,{'DebugView':8,'PomAmount':0},'Control')
        uv_noise=measured('UV repeat noise',a,b)
        c=capture('POM-On-UV',pom,{'DebugView':8,'PomAmount':1},'Control')
        response('POM UV response',a,c,.001,uv_noise)
        flat=capture('WPO-Flat-Depth',wpo,{'DebugView':6,'DisplacementAmount':0})
        repeat=capture('WPO-Flat-Depth-Repeat',wpo,{'DebugView':6,'DisplacementAmount':0})
        depth_noise=measured('Depth repeat noise',flat,repeat)
        depth=capture('WPO-On-Depth',wpo,{'DebugView':6,'DisplacementAmount':1})
        response('WPO raster depth',flat,depth,.0005,depth_noise)
        baseline={s:capture('Source-'+s+'-Baseline',s,{'DebugView':1}) for s in [pom,wpo]}
        repeat=capture('Source-Repeat',pom,{'DebugView':1})
        noise=measured('BaseColor repeat noise',baseline[pom],repeat)
        text=original.decode();uv='CkUsf_LibraryUV(In.UV, UVScale, UVRotation)';color='TintColor, NormalStrength, RoughnessScale'
        require(text.count(uv)==2 and text.count(color)==1,'Source proof anchors differ')
        mutate(text.replace(uv,uv+' * 1.17').replace(color,'TintColor * 0.1, NormalStrength, RoughnessScale').encode())
        effects={s:response('USH sampling/color '+s,baseline[s],capture('Source-'+s+'-Edited',s,{'DebugView':1}),.01,noise) for s in [pom,wpo]}
        mutate(original)
        for s in [pom,wpo]:
            error=measured('Source recovery '+s,baseline[s],capture('Source-'+s+'-Recovered',s,{'DebugView':1}))
            require(error<max(3*noise,effects[s]*.25),'Source visual recovery failed')
        before=capture('Vertex-Baseline',wpo,{'DebugView':6})
        require(text.count('(Height - 1.0)')==1,'Vertex proof anchor differs')
        mutate(text.replace('(Height - 1.0)','0.0').encode())
        edited=capture('Vertex-Edited',wpo,{'DebugView':6})
        effect=response('USH vertex height',before,edited,.0005,depth_noise)
        require(metric(flat,edited)['mean_absolute_rgb']<max(3*depth_noise,effect*.25),'Vertex edit did not flatten geometry')
        mutate(original)
        error=measured('Vertex recovery',before,capture('Vertex-Recovered',wpo,{'DebugView':6}))
        require(error<max(3*depth_noise,effect*.25),'Vertex visual recovery failed')
        require(len(report['captures'])==32 and len(report['reloads'])==4,'Incomplete diorama proof')
        report['passed']=True
    except BaseException as error:
        report['error']=str(error);raise
    finally:
        errors=[]
        def clean(label,fn):
            try:return fn()
            except BaseException as error:errors.append(label+': '+str(error))
        current=clean('source read',lambda:source.read_bytes())
        if current==owned and owned!=original:clean('source',lambda:mutate(original))
        for key in [pom,wpo]:clean(key,lambda key=key:command('select','--environment',key,*arguments(initial['environment'][key])))
        clean('quality',lambda:command('restore_quality'));clean('references',lambda:command('proof_end'))
        final=clean('state',lambda:command('state'));report['final_state']=final;report['cleanup_errors']=errors
        recovered=clean('source recovery read',lambda:source.read_bytes())
        report['restored']=bool(not errors and final and recovered==original and final['environment']==initial['environment']
                                and final['library']==initial['library'] and final['inspection_orbit']==initial['inspection_orbit']
                                and final['render_cvars']==initial['render_cvars'])
        report['passed']=report['passed'] and report['restored']
        (OUTPUT/('Diorama-'+patch+'-Proof.json')).write_text(json.dumps(report,indent=2))
    require(report['passed'],'Diorama proof failed/restoration incomplete')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--patch',choices=PATCHES)
    args=parser.parse_args()
    for patch in [args.patch] if args.patch else PATCHES:run_patch(patch)
