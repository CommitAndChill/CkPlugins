"""Serial offscreen visual/control and same-object USH proof for the bespoke patch."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from verify_industrial_reload import command, wait_reload, OUTPUT, SHADERS, LOG

SOURCE = SHADERS / 'Looks/EnvironmentWoodland.ush'
VIEWS = {'Oblique': (65, 45), 'Low': (70, 17), 'Top': (5, 70)}
IDENTITY = ['actor', 'mid', 'parent', 'mesh', 'textures', 'scale', 'colors', 'rect_intensities']


def arguments(record):
    args = sum((['--scalar', key + '=' + str(value)] for key, value in record['values'].items()), [])
    for key, values in record['colors'].items():
        args += ['--vector', key + '=' + ','.join(map(str, values))]
    return args


def pixels(filename):
    data = np.asarray(Image.open(OUTPUT / filename).convert('RGB'), dtype=float) / 255
    h, w = data.shape[:2]
    return data[int(h*.34):int(h*.67), int(w*.35):int(w*.65)]


def metric(a, b):
    delta = np.abs(a-b)
    return {'mean_absolute_rgb': float(delta.mean()), 'max_rgb': float(delta.max())}


def main():
    original = SOURCE.read_bytes()
    owned = original
    initial = command('state')
    report = {'passed': False, 'restored': False, 'initial_state': initial, 'captures': {},
              'reloads': [], 'metrics': {}, 'source_sha256': hashlib.sha256(original).hexdigest(),
              'limits': ['Native screenshots exhibit small repeat-capture differences; no exact pixel-equality claim.',
                         'POM changes UV appearance without raster silhouette/depth/shadow displacement.',
                         'WPO moves the grid vertices; collision remains unchanged; stills are not GPU timing or motion proof.']}
    if initial['preview_quality'] or initial['diagnostic_light'] is not None or initial['diagnostic_quantization']:
        raise RuntimeError('Restore all temporary presentation state before the woodland proof')
    if len(initial['library']) != 42 or set(initial['environment']) != {'pom', 'displacement'}:
        raise RuntimeError('Expected 42 preserved library looks and two woodland modes')
    root = Path(__file__).resolve().parents[2]
    manifest_path = root / 'Plugins/CkTests/Resources/CkUsf/WoodlandPatchV3/Manifest.json'
    manifest = json.loads(manifest_path.read_text())
    preparation = json.loads((OUTPUT/'WoodlandPreparation.json').read_text())
    if preparation['manifest_sha256'] != hashlib.sha256(manifest_path.read_bytes()).hexdigest():
        raise RuntimeError('Selected woodland preparation no longer matches its source')
    bindings = {channel+'Map': '/CkFoundation/CkUsf/Textures/Environment/'+info['runtime_name']+'.'+info['runtime_name']
                for channel,info in manifest['maps'].items()}
    for key, value in initial['environment'].items():
        values=value['values']
        if (value['parent'] != '/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_EnvironmentWoodland.M_CkUsf_Look_EnvironmentWoodland'
                or value['mesh'] != '/CkTests/CkUsf/Showcase/SM_UsfWoodlandGrid.SM_UsfWoodlandGrid'
                or value['textures'] != bindings or value['scale'] != [1,1,1]
                or values['TileSizeCm'] != 80 or values['HeightMip'] != 0 or values['UVScale'] != 1
                or abs(values['ReliefCm']-manifest['height']['range_cm']) > 1e-5
                or values['PomAmount'] != (1 if key=='pom' else 0)
                or values['DisplacementAmount'] != (1 if key=='displacement' else 0)):
            raise RuntimeError('The selected source, calibrated parameters and both modes must be active')
    report['manifest_sha256']=preparation['manifest_sha256']

    def capture(label, station, overrides=None, view='Oblique'):
        values = dict(initial['environment'][station]['values'])
        values.update(overrides or {})
        args = arguments({'values': values, 'colors': initial['environment'][station]['colors']})
        distance, height = VIEWS[view]
        filename = 'Woodland-' + label + '.png'
        state = command('capture', '--environment', station, '--name', filename, '--shot',
                        '--distance', distance, '--height', height, *args)['state']
        if state['pid'] != initial['pid'] or state['library'] != initial['library']:
            raise RuntimeError('Editor/library objects or values changed: ' + label)
        for key, before in initial['environment'].items():
            now = state['environment'][key]
            if any(now[field] != before[field] for field in IDENTITY) or not now['same_mid'] or not now['same_master']:
                raise RuntimeError('Woodland object or binding changed: ' + label)
        report['captures'][label] = {'image': filename, 'state': state,
                                     'sha256': hashlib.sha256((OUTPUT/filename).read_bytes()).hexdigest()}
        print('Woodland capture ' + label, flush=True)
        return pixels(filename)

    def mutate(data):
        nonlocal owned
        if SOURCE.read_bytes() != owned:
            raise RuntimeError('Concurrent shader changes preserved; stop')
        offset = LOG.stat().st_size
        owned = data
        SOURCE.write_bytes(data)
        report['reloads'].append(wait_reload(offset))

    def require_response(label, a, b, minimum, noise=0):
        result = metric(a,b)
        report['metrics'][label] = result
        result['required_mean_above_repeat_noise']=max(minimum,noise*3)
        if result['mean_absolute_rgb'] <= max(minimum,noise*3):
            raise RuntimeError('No material response above the declared display threshold: ' + label)

    try:
        command('environment_proof_begin')
        for preview in [False, True]:
            if preview: command('preview_quality')
            try:
                for station in ['pom', 'displacement']:
                    for view in VIEWS:
                        capture(('TAA' if preview else 'Native')+'-'+station+'-'+view, station, view=view)
            finally:
                if preview: command('restore_quality')
        for debug, name in [(1,'BaseColor'),(2,'Normal'),(3,'Roughness'),(5,'Height')]:
            capture('Inspect-'+name,'pom',{'DebugView':debug})
        uv_off = capture('POM-Off-UV','pom',{'DebugView':8,'PomAmount':0})
        uv_repeat = capture('POM-Off-UV-Repeat','pom',{'DebugView':8,'PomAmount':0})
        uv_noise=metric(uv_off,uv_repeat)['mean_absolute_rgb']
        report['metrics']['UV repeat noise']=metric(uv_off,uv_repeat)
        uv_on = capture('POM-On-UV','pom',{'DebugView':8,'PomAmount':1})
        require_response('POM moves sampled UVs',uv_off,uv_on,.001,uv_noise)
        flat = capture('WPO-Flat-Depth','displacement',{'DebugView':6,'DisplacementAmount':0})
        flat_repeat=capture('WPO-Flat-Depth-Repeat','displacement',{'DebugView':6,'DisplacementAmount':0})
        depth_noise=metric(flat,flat_repeat)['mean_absolute_rgb']
        report['metrics']['Depth repeat noise']=metric(flat,flat_repeat)
        depth = capture('WPO-On-Depth','displacement',{'DebugView':6,'DisplacementAmount':1})
        require_response('WPO changes raster depth',flat,depth,.0005,depth_noise)
        baseline = {}
        for station in ['pom','displacement']:
            baseline[station] = capture('Source-'+station+'-Baseline',station,{'DebugView':1})
        repeat = capture('Source-pom-Repeat','pom',{'DebugView':1})
        report['metrics']['unchanged native repeat noise'] = metric(baseline['pom'],repeat)
        bc_noise=report['metrics']['unchanged native repeat noise']['mean_absolute_rgb']
        edit_metrics={}
        text=original.decode('utf-8')
        uv='CkUsf_LibraryUV(In.UV, UVScale, UVRotation)'
        color='TintColor, NormalStrength, RoughnessScale'
        if text.count(uv)!=2 or text.count(color)!=1:
            raise RuntimeError('Unexpected woodland source-edit anchors')
        mutate(text.replace(uv,uv+' * 1.17').replace(color,'TintColor * 0.1, NormalStrength, RoughnessScale').encode())
        for station in ['pom','displacement']:
            edited=capture('Source-'+station+'-Edited',station,{'DebugView':1})
            require_response('USH sampling/color '+station,baseline[station],edited,.01,bc_noise)
            edit_metrics[station]=metric(baseline[station],edited)['mean_absolute_rgb']
        mutate(original)
        for station in ['pom','displacement']:
            recovered=capture('Source-'+station+'-Recovered',station,{'DebugView':1})
            recovery=metric(baseline[station],recovered)
            report['metrics']['source recovery display difference '+station]=recovery
            if recovery['mean_absolute_rgb'] >= max(3*bc_noise,edit_metrics[station]*.25):
                raise RuntimeError('Source did not visually recover relative to edit and measured noise')
        depth_baseline=capture('Vertex-Baseline','displacement',{'DebugView':6})
        if text.count('(Height - 1.0)')!=1: raise RuntimeError('Unexpected vertex edit anchor')
        mutate(text.replace('(Height - 1.0)','0.0').encode())
        depth_edited=capture('Vertex-Edited','displacement',{'DebugView':6})
        require_response('USH vertex height',depth_baseline,depth_edited,.0005,depth_noise)
        vertex_effect=metric(depth_baseline,depth_edited)['mean_absolute_rgb']
        if metric(flat,depth_edited)['mean_absolute_rgb'] >= max(3*depth_noise,vertex_effect*.25):
            raise RuntimeError('Vertex source flattening does not approach flat-depth control')
        mutate(original)
        depth_recovered=capture('Vertex-Recovered','displacement',{'DebugView':6})
        recovery=metric(depth_baseline,depth_recovered)
        report['metrics']['vertex recovery display difference']=recovery
        if recovery['mean_absolute_rgb'] >= max(3*depth_noise,vertex_effect*.25):
            raise RuntimeError('Vertex source did not visually recover')
        report['passed']=True
    except BaseException as error:
        report['error']=str(error)
        raise
    finally:
        errors=[]
        def cleanup(label, operation):
            try: return operation()
            except BaseException as error: errors.append(label+': '+str(error))
        if SOURCE.read_bytes()==owned and owned!=original:
            cleanup('source recovery',lambda:mutate(original))
        for key in initial['environment']:
            cleanup('station '+key,lambda key=key:command('select','--environment',key,*arguments(initial['environment'][key])))
        cleanup('quality',lambda:command('restore_quality'))
        cleanup('proof references',lambda:command('proof_end'))
        final=cleanup('final state',lambda:command('state'))
        report['final_state']=final
        report['cleanup_errors']=errors
        report['restored']=(not errors and final is not None and SOURCE.read_bytes()==original
                            and final['environment']==initial['environment'] and final['library']==initial['library']
                            and final['render_cvars']==initial['render_cvars']
                            and not final['preview_quality'] and not final['diagnostic_quantization'])
        report['passed']=report['passed'] and report['restored']
        (OUTPUT/'Woodland-Proof.json').write_text(json.dumps(report,indent=2))
    if not report['passed']: raise SystemExit(1)


if __name__=='__main__': main()
