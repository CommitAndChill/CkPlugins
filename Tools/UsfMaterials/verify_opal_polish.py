"""Explicit single-opal defaults/final/reload/motion stages. Importing performs no studio work."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import argparse,hashlib,json,math,time,traceback
import numpy as np
from PIL import Image
from opal_polish_command import submit
from opal_polish_settings import ASSET,LOOKS,TEXTURE_PREFIX
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
SOURCE=ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/OpticalOpalPolish.ush'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check_state(state):
    assert state['scene_created'] and state['adaptive']==1 and set(state['looks'])=={'Opal'}
    recipe=LOOKS['Opal'];look=state['looks']['Opal']
    assert recipe['graph']==4 and look['master'].split('.')[0]==ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name']
    assert look['front'] and look['compiled']['valid'] and look['compiled']['closure_count']==2 and not look['compiled']['compile_errors']
    for parameter,key in recipe['textures']:
        assert look['textures'][parameter].split('.')[0]==TEXTURE_PREFIX+key
    assert state['subject']=='opal'
def defaults():
    recipe=LOOKS['Opal']
    return dict(scalars={'Opal':dict(recipe['scalars'])},vectors={'Opal':{key:list(value) for key,value in recipe['vectors']}})
def check_defaults(state):
    errors=[];look=state['looks']['Opal'];recipe=LOOKS['Opal']
    for key,value in recipe['scalars']:errors.append(abs(look['scalars'][key]-value))
    for key,value in recipe['vectors']:
        assert len(look['vectors'][key])==len(value)
        errors.extend(abs(a-b) for a,b in zip(look['vectors'][key],value))
    assert errors and max(errors)<1e-5,'Persistent defaults differ; use fresh prepared scene before overrides'
    return max(errors)
def pixels(record):
    with Image.open(record['capture']) as image:return np.asarray(image.convert('RGB'),dtype=np.float32)
def mae(a,b):
    x,y=pixels(a),pixels(b);assert x.shape==y.shape;return float(np.abs(x-y).mean())
def same_objects(*records):
    assert len({r['pid'] for r in records})==1 and len({r['session_id'] for r in records})==1
    for field in ['master','mid','front']:
        assert len({r['state']['looks']['Opal'][field] for r in records})==1,field
    assert all(r['state']['looks']['Opal']['textures']==records[0]['state']['looks']['Opal']['textures'] for r in records)
class Stage:
    def __init__(self,name,data):
        self.path=OUT/('OpalPolish-'+name+'.json')
        if self.path.exists():raise RuntimeError('Preserve existing stage evidence: '+self.path.name)
        self.data=dict(data,status='running',passed=False);self.write()
    def write(self):
        pending=self.path.with_suffix('.pending')
        with pending.open('x',encoding='utf-8') as stream:json.dump(self.data,stream,indent=2)
        pending.replace(self.path)
    def capture(self,label,bucket,key,**controls):
        path=OUT/('OpalPolish-'+label+'.png')
        if path.exists():raise RuntimeError('Preserve existing capture: '+path.name)
        result=submit('capture',name=path.name,subject='opal',**controls)
        actual=Path(result['capture']).resolve()
        if actual!=path.resolve():raise RuntimeError('Unexpected capture output path')
        result['sha256']=sha(path)
        if isinstance(bucket,list):bucket.append(result)
        else:bucket[key]=result
        self.write()  # Preserve actual response/hash before any evidence assertion.
        assert result['ok'];check_state(result['state'])
        with Image.open(path) as image:assert image.size==(1600,1200)
        return result
    def finish(self):self.data.update(status='passed',passed=True);self.write();return dict(evidence=str(self.path),status='passed')
    def fail(self):self.data.update(status='failed',passed=False,failure=traceback.format_exc());self.write()
def saved_defaults():
    stage=Stage('SavedDefaults',dict(captures={}))
    try:
        initial=submit('state');stage.data['initial']=initial;stage.write()
        check_state(initial['result']);stage.data['maximum_default_error']=check_defaults(initial['result'])
        image=stage.capture('SavedDefaults',stage.data['captures'],'opal',settle_frames=40)
        assert (image['pid'],image['session_id'])==(initial['pid'],initial['session_id'])
        check_defaults(image['state']);stage.data['provenance']='Persistent-master-derived MID checked before material overrides in this stage; caller must provide a fresh scene.'
        return stage.finish()
    except Exception:stage.fail();raise
def final_proof():
    initial_path=OUT/'OpalPolish-SavedDefaults.json';initial=json.loads(initial_path.read_text());assert initial['passed']
    live=submit('state');assert (live['pid'],live['session_id'])==(initial['initial']['pid'],initial['initial']['session_id']);check_state(live['result'])
    records={};stage=Stage('FreshProof',dict(saved_defaults=dict(file=initial_path.name,sha256=sha(initial_path)),captures={'opal':records},metrics={}))
    try:
        for label in ['Final','Repeat']:stage.capture(label,records,label,settle_frames=40,**defaults())
        stage.capture('Macro',records,'Macro',camera=[18,-8,11],target=[0,0,4.1],fov=27,settle_frames=40,**defaults())
        for label,changes in [('FlashOff',{'FlashStrength':0}),('DepthOff',{'InternalDepthUV':0,'InternalLayerMix':0}),('PolishRough',{'CoatRoughness':.45})]:
            options=defaults();options['scalars']['Opal'].update(changes);stage.capture(label,records,label,settle_frames=40,**options)
        stage.capture('LightsOff',records,'LightsOff',intensities=[0,0,0],sky=0,environment_intensity=0,reflection_brightness=0,settle_frames=120,**defaults())
        stage.capture('Recovered',records,'Recovered',settle_frames=64,**defaults())
        same_objects(*records.values());assert all((r['pid'],r['session_id'])==(initial['initial']['pid'],initial['initial']['session_id']) for r in records.values())
        for label in ['Final','Repeat','Macro','Recovered']:check_defaults(records[label]['state'])
        values={label:mae(records['Final'],r) for label,r in records.items() if label not in ['Final','Macro']}
        noise=values['Repeat'];dark=pixels(records['LightsOff']);threshold=max(.1,2*noise)
        values.update(lights_off_max=float(dark.max()),lights_off_mean=float(dark.mean()),lights_off_nonzero_pixels=int(np.any(dark>0,axis=2).sum()),control_signal_threshold=threshold,control_exceeds_repeat_noise={label:values[label]>threshold for label in ['FlashOff','DepthOff','PolishRough']})
        stage.data['metrics']['opal']=values;stage.write()
        assert values['Recovered']<max(1,3*noise),('Recovery exceeds repeated-frame bound',values)
        assert dark.max()==0,('Lights-off signal remains; inspect full environment controls',values)
        assert values['FlashOff']>threshold and values['PolishRough']>threshold,('Flash/polish endpoint must exceed temporal noise',values)
        # DepthOff remains quantified even when below noise; do not imply verified physical depth.
        return stage.finish()
    except Exception:stage.fail();raise
def wait_reload(offset):
    log=ROOT/'Saved/Logs/CkPlugins.log';deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        with log.open('rb') as stream:stream.seek(offset);tail=stream.read().decode(errors='replace')
        if 'CkUsf reload batch rejected:' in tail or 'Failed to compile Material' in tail or 'error X' in tail:raise RuntimeError(tail[-6000:])
        completions=[line for line in tail.splitlines() if 'CkUsf reload complete:' in line]
        if completions:
            if '[0] failed' not in completions[-1]:raise RuntimeError(tail)
            return tail
        time.sleep(.2)
    raise RuntimeError('Watcher completion timed out; inspect the existing editor, never launch a duplicate')
def reload_proof():
    record={};stage=Stage('LiveReload',{'opal':record});original=SOURCE.read_bytes();owned=original
    try:
        needle=b'    float2 NearUV = saturate(SurfaceUV+Offset);'
        replacement=b'    float2 NearUV = saturate((SurfaceUV-.5)*1.7+.5+Offset);'
        assert original.count(needle)==1,'Unique current UV probe anchor required; inspect iterated shader source'
        record.update(source=str(SOURCE.relative_to(ROOT)),source_original_sha256=hashlib.sha256(original).hexdigest());stage.write()
        before=stage.capture('Reload-Before',record,'before',settle_frames=48,**defaults())
        repeat=stage.capture('Reload-Repeat',record,'repeat',settle_frames=48,**defaults())
        edited=original.replace(needle,replacement);assert SOURCE.read_bytes()==original,'Concurrent source edit preserved'
        offset=(ROOT/'Saved/Logs/CkPlugins.log').stat().st_size
        try:
            SOURCE.write_bytes(edited);owned=edited
            record['changed_log']=wait_reload(offset)
            stage.capture('Reload-Changed',record,'changed',settle_frames=48,**defaults())
        finally:
            if SOURCE.read_bytes()!=owned:raise RuntimeError('Concurrent shader edit preserved; inspect source before recovery')
            if owned!=original:
                offset=(ROOT/'Saved/Logs/CkPlugins.log').stat().st_size;SOURCE.write_bytes(original);owned=original
                record['restored_log']=wait_reload(offset)
            record['source_restored_sha256']=sha(SOURCE);stage.write()
        restored=stage.capture('Reload-Restored',record,'restored',settle_frames=48,**defaults())
        same_objects(before,repeat,record['changed'],restored)
        noise=mae(before,repeat);delta=mae(before,record['changed']);recovery=mae(before,restored)
        record.update(repeat_mae=noise,changed_mae=delta,restored_mae=recovery);stage.write()
        assert SOURCE.read_bytes()==original
        assert delta>max(.1,2*noise),('Rendered reload change must exceed noise',delta,noise)
        assert recovery<max(1,3*noise,delta*.25),('Reload recovery mismatch',recovery,noise,delta)
        return stage.finish()
    except Exception:stage.fail();raise
def motion():
    record={'frames':[]};stage=Stage('MotionProof',{'opal':record})
    try:
        seed=stage.capture('Motion-Seed',record,'seed',camera=[24,-11,14],settle_frames=40,**defaults())
        rig=seed['state']['rig'];target=np.asarray(rig['target'],float);camera=np.array([24,-11,14],float);offset=camera-target;base_lights=[r['position'] for r in rig['lights']]
        for frame in range(24):
            phase=2*math.pi*frame/24;angle=.18*math.sin(phase)
            position=target+np.array([math.cos(angle)*offset[0]-math.sin(angle)*offset[1],math.sin(angle)*offset[0]+math.cos(angle)*offset[1],offset[2]])
            lights=[list(p) for p in base_lights];lights[2][0]+=2*math.sin(phase);lights[2][1]+=2*math.cos(phase)
            stage.capture('Motion-%03d'%frame,record['frames'],None,camera=position.tolist(),target=target.tolist(),light_positions=lights,settle_frames=12,**defaults())
        recovered=stage.capture('Motion-Recovered',record,'recovered',settle_frames=48,**defaults())
        same_objects(seed,*record['frames'],recovered);record.update(frame_count=24,fps=8,recovered_mae=mae(seed,recovered),first_last_mae=mae(record['frames'][0],record['frames'][-1]));stage.write()
        assert len({tuple(r['state']['rig']['camera']) for r in record['frames']})>10
        return stage.finish()
    except Exception:stage.fail();raise
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['defaults','final','reload','motion']);args=parser.parse_args()
    print(json.dumps({'defaults':saved_defaults,'final':final_proof,'reload':reload_proof,'motion':motion}[args.stage](),indent=2))
