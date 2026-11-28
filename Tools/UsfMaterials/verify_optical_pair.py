"""Bounded rendered controls and same-material shader reload proof for the owned studio."""
from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
from PIL import Image
from optical_pair_command import submit
from optical_pair_settings import LOOKS

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
SHADERS=ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf'
LIGHTS=[[16,-14,19],[12,16,10],[-4,5,14]]

def capture(name,subject,**controls):
    result=submit('capture',name=name+'.png',subject=subject,**controls)
    state=result['state']
    assert state['adaptive']==1
    for role,look in state['looks'].items():
        assert look['master'].startswith('/CkFoundation/CkUsf/GeneratedLooks/')
        assert look['compiled']['valid'] and not look['compiled']['compile_errors'],(role,look)
        assert look['compiled']['closure_count']==(2 if role=='Opal' else 1)
        assert all(look['textures'].values())
    result['sha256']=hashlib.sha256((OUT/(name+'.png')).read_bytes()).hexdigest()
    return result

def defaults(subject):
    return dict(camera=[24,-11,17] if subject=='opal' else [32,-26,22],
        exposure=4.8,sky=.8,intensities=[7,3,10],light_positions=LIGHTS,
        source_radii=[.7,.45,1.2],source_lengths=[10,7,4],
        scalars={role:dict(recipe['scalars']) for role,recipe in LOOKS.items()},
        vectors={role:{key:list(value) for key,value in recipe['vectors']} for role,recipe in LOOKS.items()})

def difference(a,b):
    x=np.asarray(Image.open(OUT/(a+'.png')).convert('RGB'),dtype=np.float32)
    y=np.asarray(Image.open(OUT/(b+'.png')).convert('RGB'),dtype=np.float32)
    return float(np.abs(x-y).mean())

def wait_reload(offset):
    log=ROOT/'Saved/Logs/CkPlugins.log';deadline=time.monotonic()+50
    while time.monotonic()<deadline:
        with log.open('rb') as stream:stream.seek(offset);tail=stream.read().decode(errors='replace')
        if 'CkUsf reload complete:' in tail:
            assert '[0] failed' in tail,tail
            return tail
        time.sleep(.4)
    raise RuntimeError('Expected CkUsf source watcher reload completion')

def reload_proof():
    report={}
    for subject,file,old,new in [
        ('opal','Looks/OpticalOpal.ush','CkUsf_LibraryUV(In.UV,UVScale,UVRotation)','CkUsf_LibraryUV(In.UV,UVScale*1.7,UVRotation)'),
        ('display','Looks/OpticalCoatedGlass.ush','clamp(PolishRoughness+','clamp(.5+PolishRoughness+')]:
        prefix='OpticalPair-'+subject.title()+'-Reload'
        base=capture(prefix+'-Before',subject,settle_frames=60,**defaults(subject))
        path=SHADERS/file;original=path.read_bytes();assert original.count(old.encode())==1
        edited=original.replace(old.encode(),new.encode())
        try:
            offset=(ROOT/'Saved/Logs/CkPlugins.log').stat().st_size
            path.write_bytes(edited);changed_log=wait_reload(offset)
            changed=capture(prefix+'-Changed',subject,settle_frames=60,**defaults(subject))
        finally:
            if path.read_bytes()!=edited:raise RuntimeError('Concurrent shader edit; preserve and inspect '+str(path))
            offset=(ROOT/'Saved/Logs/CkPlugins.log').stat().st_size
            path.write_bytes(original);restored_log=wait_reload(offset)
        restored=capture(prefix+'-Restored',subject,settle_frames=60,**defaults(subject))
        for role in LOOKS:
            for field in ['master','mid']:
                assert base['state']['looks'][role][field]==changed['state']['looks'][role][field]==restored['state']['looks'][role][field]
        delta=difference(prefix+'-Before',prefix+'-Changed');recovery=difference(prefix+'-Before',prefix+'-Restored')
        assert delta>.1 and recovery<max(2,delta*.3),(delta,recovery)
        report[subject]=dict(source=file,source_restored_sha256=hashlib.sha256(original).hexdigest(),changed_delta=delta,restored_delta=recovery,
            before=base,changed=changed,restored=restored,changed_log=changed_log,restored_log=restored_log)
    (OUT/'OpticalPair-LiveReload.json').write_text(json.dumps(report,indent=2))

def final_proof():
    results={}
    initial=submit('state')['result']
    # Prove saved defaults before any capture can apply transient overrides.
    for role,recipe in LOOKS.items():
        actual=initial['looks'][role]
        for key,value in recipe['scalars']:assert abs(actual['scalars'][key]-value)<1e-5,(role,key)
        for key,value in recipe['vectors']:assert all(abs(a-b)<1e-5 for a,b in zip(actual['vectors'][key],value)),(role,key)
    (OUT/'OpticalPair-SavedDefaults.json').write_text(json.dumps(initial,indent=2))
    for subject in ['opal','display']:
        prefix='OpticalPair-'+('Opal' if subject=='opal' else 'Display')
        options=defaults(subject)
        results[prefix+'-Final']=capture(prefix+'-Final',subject,settle_frames=80,**options)
        role,param=('Opal','FlashStrength') if subject=='opal' else ('GlassCover','CoatingStrength')
        options['scalars'][role][param]=0
        endpoint='-Plain' if subject=='opal' else '-Clear'
        results[prefix+endpoint]=capture(prefix+endpoint,subject,settle_frames=40,**options)
        options=defaults(subject);options.update(sky=0,intensities=[0,0,0])
        results[prefix+'-LightsOff']=capture(prefix+'-LightsOff',subject,settle_frames=100,**options)
        options=defaults(subject);options['camera']=[26,9,15] if subject=='opal' else [25,30,19]
        results[prefix+'-Angle']=capture(prefix+'-Angle',subject,settle_frames=60,**options)
        results[prefix+'-Recovered']=capture(prefix+'-Recovered',subject,settle_frames=60,**defaults(subject))
    (OUT/'OpticalPair-FreshProof.json').write_text(json.dumps(results,indent=2))

def motion():
    results={}
    for subject in ['opal','display']:
        options=defaults(subject);prefix='OpticalPair-'+subject.title()+'-Motion'
        entries=[]
        for frame in range(36):
            phase=2*math.pi*frame/36
            options['light_positions']=[[18*math.cos(phase),18*math.sin(phase),17],LIGHTS[1],LIGHTS[2]]
            entries.append(capture(prefix+f'-{frame:03d}',subject,settle_frames=8,**options))
        results[subject]=entries
    (OUT/'OpticalPair-MotionProof.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['reload','final','motion']);args=parser.parse_args()
    {'reload':reload_proof,'final':final_proof,'motion':motion}[args.stage]()
