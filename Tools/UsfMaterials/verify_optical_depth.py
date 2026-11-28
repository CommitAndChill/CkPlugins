"""Explicit opt-in depth-studio evidence stages. Importing this file performs no studio work.

Run defaults/final only immediately after a fresh prepared scene, before MID edits.
Reload temporarily edits exactly two depth .ush files and restores their original bytes.
Motion makes 24 independent captures per subject. Each stage writes its own evidence.
"""
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
from optical_depth_command import submit
from optical_depth_settings import ASSET, LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Saved/UsfMaterialGallery'
SHADERS = ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'


def save(name, data):
    path = OUT/('OpticalDepth-'+name+'.json')
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
    result = submit('capture',name='OpticalDepth-'+name+'.png',subject=subject,**controls)
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
    images = {subject:capture(subject.title()+'-SavedDefaults',subject,settle_frames=32) for subject in ['opal','display']}
    same_objects(*images.values())
    assert all(image['pid']==response['pid'] and image['session_id']==response['session_id'] for image in images.values())
    report = dict(initial=response,maximum_default_error=maximum_error,captures=images,
                  provenance='Initial persistent-master-derived MIDs checked before any material override in this invocation; requires a fresh scene from the caller.')
    path = save('SavedDefaults',report)
    return dict(evidence=path,maximum_default_error=maximum_error)


def final_proof():
    # Preserve the evidence recorded before the first MID override in this boot.
    initial_path = OUT/'OpticalDepth-SavedDefaults.json'
    initial_report = json.loads(initial_path.read_text())
    live = submit('state')
    assert (live['pid'],live['session_id']) == (initial_report['initial']['pid'],initial_report['initial']['session_id'])
    check_state(live['result'])
    initial = dict(evidence=str(initial_path),maximum_default_error=initial_report['maximum_default_error'])
    report = dict(saved_defaults=initial,captures={},metrics={})
    for subject in ['opal','display']:
        title = subject.title()
        records = {}
        records['Final'] = capture(title+'-Final',subject,settle_frames=32,**material_defaults())
        records['Repeat'] = capture(title+'-Repeat',subject,settle_frames=32,**material_defaults())
        if subject=='opal':
            options = material_defaults(); options['scalars']['Opal']['FlashStrength']=0
            records['FlashOff'] = capture(title+'-FlashOff',subject,settle_frames=32,**options)
            options = material_defaults(); options['scalars']['Opal'].update(InternalDepthUV=0,InternalLayerMix=0)
            records['DepthOff'] = capture(title+'-DepthOff',subject,settle_frames=32,**options)
        else:
            options = material_defaults(); options['scalars']['GlassCover']['CoatingStrength']=0
            records['Uncoated'] = capture(title+'-Uncoated',subject,settle_frames=32,**options)
            records['CoverOff'] = capture(title+'-CoverOff',subject,visible={'GlassCover':False},settle_frames=32,**material_defaults())
        records['LightsOff'] = capture(title+'-LightsOff',subject,sky=0,intensities=[0,0,0],settle_frames=120,**material_defaults())
        records['Recovered'] = capture(title+'-Recovered',subject,settle_frames=40,**material_defaults())
        same_objects(*records.values())
        metrics = {stage:mae(records['Final'],value) for stage,value in records.items() if stage!='Final'}
        dark = pixels(records['LightsOff'])
        metrics.update(lights_off_max=float(dark.max()),lights_off_mean=float(dark.mean()),
                       lights_off_nonzero_pixels=int(np.any(dark>0,axis=2).sum()))
        report['captures'][subject]=records; report['metrics'][subject]=metrics
        save('FreshProof',report)
        # Repeat supplies the temporal-noise baseline; report subtle control effects honestly.
        assert metrics['Recovered']<max(.75,3*metrics['Repeat']), (subject,'recovery',metrics)
        if subject=='opal':
            assert metrics['lights_off_max']==0, ('Opal unexpected lights-off signal',metrics)
        else:
            assert metrics['lights_off_nonzero_pixels']>100 and metrics['lights_off_max']>32, ('Display graphic disappeared',metrics)
    return dict(evidence=str(OUT/'OpticalDepth-FreshProof.json'),metrics=report['metrics'])


def wait_reload(offset):
    path = ROOT/'Saved/Logs/CkPlugins.log'
    deadline = time.monotonic()+50
    while time.monotonic()<deadline:
        with path.open('rb') as stream:
            stream.seek(offset); tail=stream.read().decode(errors='replace')
        completions=[line for line in tail.splitlines() if 'CkUsf reload complete:' in line]
        if completions:
            assert '[0] failed' in completions[-1],tail
            return tail
        time.sleep(.25)
    raise RuntimeError('Expected actual CkUsf watcher reload completion; do not duplicate editor')


def reload_proof():
    report = {}
    probes = [('opal','OpticalOpalDepth.ush',
               'A.UV = saturate(In.UV+Offset);','A.UV = saturate((In.UV-.5)*1.7+.5+Offset);'),
              ('display','OpticalDepthGlass.ush',
               'NormalStrength,PolishRoughness,GlassIor,CoatingIor,',
               'NormalStrength,.55+PolishRoughness,GlassIor,CoatingIor,')]
    for subject,filename,old,new in probes:
        prefix=subject.title()+'-Reload'
        path=SHADERS/filename; original=path.read_bytes()
        assert original.count(old.encode())==1, ('Probe source must match exactly once',filename)
        before=capture(prefix+'-Before',subject,settle_frames=40,**material_defaults())
        repeat=capture(prefix+'-Repeat',subject,settle_frames=40,**material_defaults())
        noise=mae(before,repeat)
        edited=original.replace(old.encode(),new.encode())
        # Compare ownership immediately before mutation and restore only our exact probe bytes.
        assert path.read_bytes()==original, ('Concurrent source edit',filename)
        offset=(ROOT/'Saved/Logs/CkPlugins.log').stat().st_size
        path.write_bytes(edited)
        try:
            changed_log=wait_reload(offset)
            changed=capture(prefix+'-Changed',subject,settle_frames=40,**material_defaults())
        finally:
            if path.read_bytes()!=edited:
                raise RuntimeError('Concurrent shader edit: preserve and inspect '+str(path))
            offset=(ROOT/'Saved/Logs/CkPlugins.log').stat().st_size
            path.write_bytes(original)
            restored_log=wait_reload(offset)
        restored=capture(prefix+'-Restored',subject,settle_frames=40,**material_defaults())
        same_objects(before,repeat,changed,restored)
        delta,recovery=mae(before,changed),mae(before,restored)
        assert path.read_bytes()==original
        report[subject]=dict(source=str(path.relative_to(ROOT)),source_restored_sha256=hashlib.sha256(original).hexdigest(),
            repeat_mae=noise,changed_mae=delta,restored_mae=recovery,before=before,repeat=repeat,changed=changed,restored=restored,
            changed_log=changed_log,restored_log=restored_log)
        save('LiveReload',report)
        assert delta>max(.1,noise*2), (subject,'Rendered edit must exceed repeated-frame noise',delta,noise)
        assert recovery<max(.75,noise*3,delta*.25), (subject,'Restoration mismatch',recovery,noise,delta)
    return dict(evidence=str(OUT/'OpticalDepth-LiveReload.json'),metrics={key:{k:v[k] for k in ['repeat_mae','changed_mae','restored_mae']} for key,v in report.items()})


def motion(subjects):
    report = {}
    for subject in subjects:
        # Establish the caller's current session subject defaults, then derive movement
        # from the returned rig rather than copying camera/light presets into this file.
        seed=capture(subject.title()+'-Motion-Seed',subject,settle_frames=24,**material_defaults())
        rig=seed['state']['rig']; camera=np.array(rig['camera'],float); target=np.array(rig['target'],float)
        base_lights=[record['position'] for record in rig['lights']]
        entries=[]
        for frame in range(24):
            phase=2*math.pi*frame/24
            angle=math.radians(9)*math.sin(phase)
            offset=camera-target
            moved=target+np.array([math.cos(angle)*offset[0]-math.sin(angle)*offset[1],
                                  math.sin(angle)*offset[0]+math.cos(angle)*offset[1],offset[2]+.7*math.sin(phase)])
            lights=[list(position) for position in base_lights]
            lights[0][0]+=3*math.sin(phase);lights[0][1]+=3*math.cos(phase)
            entries.append(capture(subject.title()+f'-Motion-{frame:03d}',subject,camera=moved.tolist(),target=target.tolist(),
                light_positions=lights,settle_frames=8,**material_defaults()))
        recovered=capture(subject.title()+'-Motion-Recovered',subject,settle_frames=32,**material_defaults())
        same_objects(seed,*entries,recovered)
        report[subject]=dict(seed=seed,frames=entries,recovered=recovered,frame_count=24,
            first_last_mae=mae(entries[0],entries[-1]),recovered_mae=mae(seed,recovered))
        save('MotionProof',report)
    return dict(evidence=str(OUT/'OpticalDepth-MotionProof.json'),frames={key:value['frame_count'] for key,value in report.items()})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['defaults','final','reload','motion'])
    parser.add_argument('--subject',choices=['opal','display','both'],default='both',help='Motion subject; other stages cover both subjects')
    args=parser.parse_args()
    if args.stage=='motion':
        result=motion(['opal','display'] if args.subject=='both' else [args.subject])
    else:
        result={'defaults':saved_defaults,'final':final_proof,'reload':reload_proof}[args.stage]()
    print(json.dumps(result,indent=2))
