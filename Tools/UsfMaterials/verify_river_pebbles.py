"""Serial offscreen river-pebble proof; execute only when authorized by the lead.

Adapted from the existing woodland 32-capture/four-reload proof. Requires the
inspection orbit disabled throughout; never changes its state or editor lifetime.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from verify_industrial_reload import command, wait_reload, OUTPUT, SHADERS, LOG

SOURCE = SHADERS / 'Looks/EnvironmentRiverPebbles.ush'
VIEWS = {'Oblique': (65, 45), 'Low': (70, 17), 'Top': (5, 70), 'Control': (65, 30)}
IDENTITY = ['actor', 'mid', 'parent', 'mesh', 'textures', 'scale', 'colors', 'rect_intensities']


def orbit_is_off(state):
    orbit = state.get('inspection_orbit')
    return (isinstance(orbit, dict) and orbit.get('enabled') is False
            and orbit.get('intensity') == 0 and orbit.get('target') is None)


def require_orbit_off(state, expected=None):
    if not orbit_is_off(state):
        raise RuntimeError('Inspection orbit must be explicitly disabled before/during/after the river-pebble proof')
    if expected is not None and state['inspection_orbit'] != expected:
        raise RuntimeError('Inspection orbit phase/pause/actual-light state changed during the proof')


def validate_initial(initial, manifest, preparation, manifest_sha):
    """Pure schema/default gate, also usable with saved-state fixtures offline."""
    require_orbit_off(initial)
    if initial['preview_quality'] or initial['diagnostic_light'] is not None or initial['diagnostic_quantization']:
        raise RuntimeError('Restore all temporary presentation state before the river-pebble proof')
    if len(initial['library']) != 42 or set(initial['environment']) != {'pom', 'displacement'}:
        raise RuntimeError('Expected42preserved library looks and two river-pebble modes')
    if preparation['manifest_sha256'] != manifest_sha:
        raise RuntimeError('Selected river-pebble preparation no longer matches its source')
    material = manifest['materials']['pebbles']
    maps = material['maps']
    if material['look_id'] != 'EnvironmentRiverPebbles' or set(maps) != {'BaseColor','Normal','Roughness','Height','AO'}:
        raise RuntimeError('Expected selectedriver-pebble identity and fivecanonical maps')
    for channel, info in maps.items():
        expected_name = 'T_EnvironmentRiverPebblesBC8_BaseColor' if channel=='BaseColor' else 'T_EnvironmentRiverPebbles_'+channel
        if (info['width'] != 2048 or info['height'] != 2048 or info['runtime_name'] != expected_name
                or (channel=='BaseColor' and info['bit_depth']!=8)
                or (channel in ['Normal','Height'] and info['bit_depth']!=16)):
            raise RuntimeError('Expected aligned2Kriver-pebble maps: '+channel)
    relief = preparation['height']['authored_relief_cm']
    if not isinstance(relief, (int,float)) or not np.isfinite(relief) or not 0 < relief <= 6:
        raise RuntimeError('Authored relief must be finite and fit the existing6cmgrid bound')
    bindings = {channel+'Map': '/CkFoundation/CkUsf/Textures/Environment/'+info['runtime_name']+'.'+info['runtime_name']
                for channel, info in maps.items()}
    for key, value in initial['environment'].items():
        values=value['values']
        if (value['parent'] != '/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_EnvironmentRiverPebbles.M_CkUsf_Look_EnvironmentRiverPebbles'
                or value['mesh'] != '/CkTests/CkUsf/Showcase/SM_UsfWoodlandGrid.SM_UsfWoodlandGrid'
                or value['textures'] != bindings or value['scale'] != [1,1,1]
                or values['TileSizeCm'] != 80 or values['HeightMip'] != 0 or values['UVScale'] != 1
                or values['NormalStrength'] != 1 or values['StepCount'] != 64 or values['DebugView'] != 0
                or not np.isfinite(values['ReliefCm']) or abs(values['ReliefCm']-relief) > 1e-5
                or values['PomAmount'] != (1 if key=='pom' else 0)
                or values['DisplacementAmount'] != (1 if key=='displacement' else 0)):
            raise RuntimeError('Selectedsource, authoreddefaults and bothmodes must be active')


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
                         'WPO moves the grid vertices; collision remains unchanged; stills are not GPU timing or motion proof.',
                         'A heightfield approximates the scanned rounded solids; it cannot preserve every overhang, undercut or independent-stone silhouette.',
                         'Published216cm source is presented at authored80cm; relief is normal-consistency-guided, not physically calibrated.']}
    root = Path(__file__).resolve().parents[2]
    manifest_path = root / 'Plugins/CkTests/Resources/CkUsf/PebbleReferenceV1/Manifest-runtime-v2.json'
    manifest = json.loads(manifest_path.read_text())
    preparation = json.loads((OUTPUT/'RiverPebblesPreparation.json').read_text())
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    validate_initial(initial, manifest, preparation, manifest_sha)
    report['manifest_sha256'] = manifest_sha
    report['preparation_sha256'] = hashlib.sha256((OUTPUT/'RiverPebblesPreparation.json').read_bytes()).hexdigest()
    report['authored_relief_cm'] = preparation['height']['authored_relief_cm']

    def capture(label, station, overrides=None, view='Oblique'):
        values = dict(initial['environment'][station]['values'])
        values.update(overrides or {})
        args = arguments({'values': values, 'colors': initial['environment'][station]['colors']})
        distance, height = VIEWS[view]
        filename = 'RiverPebbles-' + label + '.png'
        state = command('capture', '--environment', station, '--name', filename, '--shot',
                        '--distance', distance, '--height', height, *args)['state']
        require_orbit_off(state, initial['inspection_orbit'])
        if state['pid'] != initial['pid'] or state['library'] != initial['library']:
            raise RuntimeError('Editor/library objects or values changed: ' + label)
        for key, before in initial['environment'].items():
            now = state['environment'][key]
            if any(now[field] != before[field] for field in IDENTITY) or not now['same_mid'] or not now['same_master']:
                raise RuntimeError('River-pebble object or binding changed: ' + label)
        report['captures'][label] = {'image': filename, 'state': state,
                                     'sha256': hashlib.sha256((OUTPUT/filename).read_bytes()).hexdigest()}
        print('RiverPebbles capture ' + label, flush=True)
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
                    for view in ['Oblique','Low','Top']:
                        capture(('TAA' if preview else 'Native')+'-'+station+'-'+view, station, view=view)
            finally:
                if preview: command('restore_quality')
        for debug, name in [(1,'BaseColor'),(2,'Normal'),(3,'Roughness'),(5,'Height')]:
            capture('Inspect-'+name,'pom',{'DebugView':debug})
        uv_off = capture('POM-Off-UV','pom',{'DebugView':8,'PomAmount':0},view='Control')
        uv_repeat = capture('POM-Off-UV-Repeat','pom',{'DebugView':8,'PomAmount':0},view='Control')
        uv_noise=metric(uv_off,uv_repeat)['mean_absolute_rgb']
        report['metrics']['UV repeat noise']=metric(uv_off,uv_repeat)
        uv_on = capture('POM-On-UV','pom',{'DebugView':8,'PomAmount':1},view='Control')
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
            raise RuntimeError('Unexpected river-pebble source-edit anchors')
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
        if len(report['captures']) != 32 or len(report['reloads']) != 4:
            raise RuntimeError('Expected exactly32captures/four successfulsource reloads')
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
                            and final['pid']==initial['pid']
                            and final['environment']==initial['environment'] and final['library']==initial['library']
                            and final['render_cvars']==initial['render_cvars']
                            and not final['preview_quality'] and not final['diagnostic_quantization']
                            and final['diagnostic_light'] is None
                            and orbit_is_off(final)
                            and final['inspection_orbit']==initial['inspection_orbit'])
        report['passed']=report['passed'] and report['restored']
        (OUTPUT/'RiverPebbles-Proof.json').write_text(json.dumps(report,indent=2))
    if not report['passed']: raise SystemExit(1)


if __name__=='__main__': main()
