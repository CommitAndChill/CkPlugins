"""Explicit seated-display evidence stages; import performs no studio work."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import math
import time
import numpy as np
from PIL import Image
from optical_seated_command import submit
from optical_seated_settings import ASSET, LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Saved/UsfMaterialGallery'
SHADERS = ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'


def save(name, data):
    path = OUT/('OpticalSeated-'+name+'.json')
    path.write_text(json.dumps(data,indent=2)+'\n')
    return str(path)


def check_state(state):
    assert state['scene_created'] and state['adaptive']==1, 'Owned Adaptive scene required'
    assert set(state['looks'])==set(LOOKS), 'Five exact role records required'
    for role,recipe in LOOKS.items():
        look = state['looks'][role]
        path = ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name']
        assert look['master'].split('.')[0]==path, (role,'master')
        assert bool(look['front']) == (recipe['graph'] in [4,6]), (role,'native front material versus converted surface')
        assert look['compiled']['valid'] and not look['compiled']['compile_errors'], (role,look['compiled'])
        assert look['compiled']['closure_count']==(2 if role=='Opal' else 1), (role,'closures')
        for parameter,key in recipe['textures']:
            assert look['textures'][parameter].split('.')[0]==ASSET+'/Textures/Optical/Pair/T_OpticalPair_'+key, (role,parameter)


def material_defaults():
    # Rig defaults come from the live session's subject_defaults, avoiding copied presets.
    return dict(scalars={role:dict(recipe['scalars']) for role,recipe in LOOKS.items()},
                vectors={role:{key:list(value) for key,value in recipe['vectors']} for role,recipe in LOOKS.items()})


def capture(name, subject, **controls):
    result = submit('capture',name='OpticalSeated-'+name+'.png',subject=subject,**controls)
    check_state(result['state'])
    assert result['state']['subject']==subject
    path = Path(result['capture'])
    assert path.resolve().parent==OUT.resolve()
    result['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def pixels(capture_result):
    with Image.open(capture_result['capture']) as image:
        return np.asarray(image.convert('RGB'),dtype=np.float32)


def mae(a,b):
    x,y = pixels(a),pixels(b)
    assert x.shape==y.shape
    return float(np.abs(x-y).mean())


def same_objects(*results):
    assert len({result['pid'] for result in results})==1, 'Editor PID changed'
    assert len({result['session_id'] for result in results})==1, 'Owned session changed'
    for role in LOOKS:
        for field in ['master','mid']:
            assert len({result['state']['looks'][role][field] for result in results})==1, (role,field)


def saved_defaults():
    response = submit('state')
    state = response['result']
    check_state(state)
    maximum_error = 0
    for role,recipe in LOOKS.items():
        for key,value in recipe['scalars']:
            error = abs(state['looks'][role]['scalars'][key]-value)
            assert error<1e-5, (role,key,'MID already changed; use a fresh prepared scene')
            maximum_error = max(maximum_error,error)
        for key,value in recipe['vectors']:
            actual = state['looks'][role]['vectors'][key]
            assert len(actual)==len(value)
            error = max(abs(a-b) for a,b in zip(actual,value))
            assert error<1e-5, (role,key,'MID already changed; use a fresh prepared scene')
            maximum_error = max(maximum_error,error)
    # State is acquired before either capture. Neither capture supplies material overrides.
    images = {subject:capture(subject.title()+'-SavedDefaults',subject,settle_frames=32) for subject in ['display']}
    same_objects(*images.values())
    assert all(image['pid']==response['pid'] and image['session_id']==response['session_id'] for image in images.values())
    report = dict(initial=response,maximum_default_error=maximum_error,captures=images,
                  provenance='Initial persistent-master-derived MIDs checked before any material override in this invocation; requires a fresh scene from the caller.')
    path = save('SavedDefaults',report)
    return dict(evidence=path,maximum_default_error=maximum_error)


MACRO=dict(camera=[20,-25,9],target=[4,-6,2.3],fov=23)


def final_proof():
    initial=json.loads((OUT/'OpticalSeated-SavedDefaults.json').read_text())
    live=submit('state')
    assert (live['pid'],live['session_id'])==(initial['initial']['pid'],initial['initial']['session_id'])
    check_state(live['result'])
    records={}
    records['Final']=capture('Display-Final','display',settle_frames=120,**material_defaults())
    records['Repeat']=capture('Display-Repeat','display',settle_frames=120,**material_defaults())
    records['Macro']=capture('Display-Macro','display',settle_frames=120,**MACRO,**material_defaults())
    controls=material_defaults();controls['scalars']['GlassCover']['BevelFilmStrength']=0
    records['Uncoated']=capture('Display-Uncoated','display',settle_frames=120,**controls)
    records['GlassOff']=capture('Display-GlassOff','display',visible={'GlassCover':False},settle_frames=120,**material_defaults())
    controls=material_defaults()
    for role in ['Housing','MetalTrim']:
        controls['scalars'][role].update(UVScale=2.7,UVRotation=70,NormalStrength=.7,RoughnessBias=.35)
        controls['vectors'][role]['TintColor']=[.20,.36,.58,1]
    records['MetalControls']=capture('Display-MetalControls','display',settle_frames=120,**controls)
    controls=material_defaults();controls['scalars']['Panel']['EmissionStrength']=0
    records['LightsOff']=capture('Display-LightsOff','display',intensities=[0,0,0],sky=0,
        environment_intensity=0,reflection_brightness=0,settle_frames=120,**controls)
    records['Recovered']=capture('Display-Recovered','display',settle_frames=120,**material_defaults())
    same_objects(*records.values())
    noise=mae(records['Final'],records['Repeat'])
    metrics={key:mae(records['Final'],records[key]) for key in ['Uncoated','GlassOff','MetalControls','Recovered']}
    # The fixed hero camera places the front chamfer in this region. Its small
    # color change must be compared with temporal noise in the same pixels,
    # rather than noise from the entire environment and housing.
    region=(slice(570,810),slice(680,1490))
    baseline=pixels(records['Final'])[region]
    bevel_noise=float(np.abs(baseline-pixels(records['Repeat'])[region]).mean())
    bevel_change=float(np.abs(baseline-pixels(records['Uncoated'])[region]).mean())
    assert metrics['Recovered']<max(noise*3,.15),metrics
    black_max=float(pixels(records['LightsOff']).max())
    report=dict(saved_defaults=initial,captures=records,repeat_noise_mae=noise,metrics=metrics,
        lights_off_max_8bit=black_max,
        bevel_region=dict(bounds_xyxy=[680,570,1490,810],repeat_noise_mae=bevel_noise,uncoated_mae=bevel_change),
        sources={name:hashlib.sha256((SHADERS/name).read_bytes()).hexdigest() for name in ['OpticalSeatedGlass.ush','OpticalSeatedAluminum.ush']})
    path=save('FreshProof',report)
    assert all(metrics[key]>max(noise*3,.05) for key in ['GlassOff','MetalControls']),metrics
    assert bevel_change>max(bevel_noise*3,.05),report['bevel_region']
    assert black_max<=1,black_max
    return path


def reload_proof():
    from verify_optical_depth import wait_reload
    report={}
    probes=[('Glass','OpticalSeatedGlass.ush',
        'TransmissionColor,UVScale,UVRotation,NormalStrength,PolishRoughness,GlassIor,CoatingIor,',
        'TransmissionColor,UVScale*2.0,UVRotation+25.0,max(NormalStrength,.8),.4+PolishRoughness,GlassIor,CoatingIor,'),
        ('Aluminum','OpticalSeatedAluminum.ush',
        'O.BaseColor = saturate(TintColor*(.9+Detail*.2));',
        'O.BaseColor = saturate(TintColor*float3(.25,.5,.8)*(.9+Detail*.2));')]
    log=ROOT/'Saved/Logs/CkPlugins.log'
    for name,filename,anchor,replacement in probes:
        path=SHADERS/filename;original=path.read_bytes();assert original.count(anchor.encode())==1
        before=capture('Display-Reload'+name+'-Before','display',settle_frames=64,**material_defaults())
        edited=original.replace(anchor.encode(),replacement.encode())
        try:
            offset=log.stat().st_size;path.write_bytes(edited);changed_log=wait_reload(offset)
            changed=capture('Display-Reload'+name+'-Changed','display',settle_frames=64,**material_defaults())
        finally:
            if path.read_bytes()!=edited:raise RuntimeError('Concurrent source edit preserved: '+filename)
            offset=log.stat().st_size;path.write_bytes(original);restored_log=wait_reload(offset)
        restored=capture('Display-Reload'+name+'-Restored','display',settle_frames=64,**material_defaults())
        same_objects(before,changed,restored)
        change,restore=mae(before,changed),mae(before,restored)
        assert change>max(restore*3,.05),(name,change,restore)
        assert path.read_bytes()==original
        report[name]=dict(before=before,changed=changed,restored=restored,change_mae=change,restore_mae=restore,
            original_sha256=hashlib.sha256(original).hexdigest(),restored_exactly=True,
            reload_log=changed_log,restore_log=restored_log)
    return save('LiveReload',report)


def motion_proof():
    frames=[]
    angle=math.atan2(-27,17);radius=math.hypot(17,27)
    for index in range(24):
        phase=2*math.pi*index/24
        view=angle+.24*math.sin(phase)
        frames.append(capture(f'Display-Motion-{index:03d}','display',
            camera=[radius*math.cos(view),radius*math.sin(view),13],
            light_positions=[[-4,-12,1],[8,-3,1],[16*math.cos(phase),16*math.sin(phase),8]],
            intensities=[.0025,.0025,.001],settle_frames=40,**material_defaults()))
    same_objects(*frames)
    assert len({frame['sha256'] for frame in frames})==24
    return save('MotionProof',{'display':dict(frames=frames,fps=8,
        description='Actual native frames: camera sweeps the front corner while a third light circles the display; no frame interpolation.')})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['defaults','final','reload','motion'])
    stage=parser.parse_args().stage
    print({'defaults':saved_defaults,'final':final_proof,'reload':reload_proof,'motion':motion_proof}[stage]())

