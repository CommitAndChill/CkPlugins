"""Explicit native-primary live-reload proof for the single-mesh native layered study.

Importing performs no filesystem writes, shader edits, or studio commands.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import argparse,hashlib,json,re,time,traceback,uuid
import numpy as np
from PIL import Image
from opal_layered_command import submit

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
LOG=ROOT/'Saved/Logs/CkPlugins.log'
SHADERS=ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'
BACKEND='AutomationLibrary.take_high_res_screenshot primary editor viewport'
ROLES={'Opal'}
PROBES={'Opal':('OpticalOpalLayered.ush',b'    O.BDiffuseAlbedo = saturate(lerp(MilkColor * ScatteringStrength,.85 * PatchTint,Activity));',b'    O.BDiffuseAlbedo = float3(.02,.7,.02);')}


def require(condition,message):
    if not condition:raise AssertionError(message)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def pixels(record):
    with Image.open(record['capture']) as image:
        require(image.size==(1600,1200),'Expected actual 1600x1200 native capture')
        return np.asarray(image.convert('RGB'),dtype=np.float32)

def mae(first,second):return float(np.abs(pixels(first)-pixels(second)).mean())

def wait_reload(offset):
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        with LOG.open('rb') as stream:stream.seek(offset);tail=stream.read().decode(errors='replace')
        if any(marker in tail.lower() for marker in ['ckusf reload batch rejected:','failed to compile material','error x','logshadercompilers: error','logmaterial: error','shadercompileworker failed','fatal error','ensure condition failed']):
            raise RuntimeError(tail[-8000:])
        completions=[line for line in tail.splitlines() if 'CkUsf reload complete:' in line]
        if completions:
            require('[0] failed' in completions[-1],'Watcher reload completion reported failures: '+tail[-8000:])
            return tail
        time.sleep(.2)
    raise RuntimeError('Watcher completion timed out; inspect existing session, do not regenerate or launch another editor')


def material_identity(record):
    return {role:{key:record['state']['looks'][role][key] for key in ['master','mid','front','textures','scalars','vectors']} for role in ROLES}


def same_identity(first,record):
    require((record['pid'],record['session_id'])==(first['pid'],first['session_id']),'Process/session changed')
    require(material_identity(record)==material_identity(first),'Material/MID/front/texture/parameter state changed')
    require(record['state']['actors']==first['state']['actors'],'Actor mesh/transform changed')
    require(record['state']['rig']==first['state']['rig'],'Fixed camera/lighting/postprocess rig changed')
    require(record['primary_camera']==first['primary_camera'] and record['primary_camera_state']==first['primary_camera_state'],'Actual primary camera state changed')


class Proof:
    def __init__(self,probes,prefix):
        require(isinstance(prefix,str) and re.fullmatch(r'OpalLayered-Reload(?:-[A-Za-z0-9]+)*',prefix),'Plain owned OpalLayered-Reload prefix required')
        self.prefix=prefix
        self.path=OUT/(prefix+'-Proof.json')
        labels=['Baseline','Repeat']+[role+'-'+phase for role in probes for phase in ['Changed','Restored']]
        require(not self.path.exists(),'Preserve existing depth reload receipt')
        for label in labels:require(not (OUT/(self.prefix+'-'+label+'.png')).exists(),'Preserve existing reload capture: '+label)
        self.data=dict(status='running',passed=False,prefix=prefix,selected_roles=list(probes),captures={},probes={},limitations=['Rendered live-reload proof only; visual approval, volumetric transport and performance remain separate.'])
        self.write()
    def write(self):
        temporary=self.path.with_suffix('.pending')
        with temporary.open('x',encoding='utf-8') as stream:json.dump(self.data,stream,indent=2)
        temporary.replace(self.path)
    def capture(self,label):
        path=OUT/(self.prefix+'-'+label+'.png')
        require(not path.exists(),'Preserve existing reload capture')
        record=submit('capture_primary',name=path.name,subject='opal',visible={'Opal':True},
            camera=[24,-11,14],target=[0,0,4.1],fov=32,settle_frames=64)
        self.data['captures'][label]=record;self.write()  # Preserve actual response before checking it.
        require(Path(record['capture']).resolve()==path.resolve(),'Unexpected native capture path')
        record['sha256']=sha(path);self.write()
        require(record['ok'] and record.get('capture_backend')==BACKEND and record.get('native_task_done') is True and record.get('native_task_valid') is True,'Completed native primary screenshot required')
        uuid.UUID(record['id']);uuid.UUID(record['session_id']);pixels(record)
        state=record['state'];require(state['adaptive']==1 and set(state['looks'])==set(state['actors'])==ROLES and state['visible']=={role:True for role in ROLES},'Expected visible single-actor Adaptive layered study')
        for role,look in state['looks'].items():
            compiled=look['compiled'];require(compiled['valid'] and not compiled['compile_errors'] and compiled['closure_count']==2,'Invalid native compiled role: '+role)
            require(not compiled['has_glint'] and not compiled['complex_special'],'Native glint material contract differs')
        require(state['looks']['Opal']['master']=='/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_OpticalOpalLayeredFire.M_CkUsf_Look_OpticalOpalLayeredFire','Exact single layered master required')
        require(np.allclose(state['actors']['Opal']['position'],[0,0,0],atol=1e-5,rtol=0) and np.allclose(state['actors']['Opal']['scale'],[1,1,1],atol=1e-5,rtol=0) and all(abs(value)<1e-5 for value in state['actors']['Opal']['rotation'].values()),'Single identity Body actor required')
        require(record.get('primary_camera_state')==state.get('primary_camera_state') and record['primary_camera_state'],'Actual primary camera sampling required')
        require(np.allclose(state['rig']['camera'],[24,-11,14],atol=1e-5,rtol=0) and np.allclose(state['rig']['target'],[0,0,4.1],atol=1e-5,rtol=0) and abs(state['rig']['fov']-32)<1e-5,'Fixed default camera required')
        first=self.data['captures'].get('Baseline')
        if first is not record:same_identity(first,record)
        return record


def main(prefix='OpalLayered-Reload'):
    probes=PROBES
    # Validate selected unique anchors before requesting any capture or editing source.
    originals={role:(SHADERS/filename).read_bytes() for role,(filename,_,_) in probes.items()}
    for role,(_,needle,_) in probes.items():require(originals[role].count(needle)==1,'Unique current source assignment required: '+role)
    proof=Proof(probes,prefix)
    try:
        baseline=proof.capture('Baseline');repeat=proof.capture('Repeat');noise=mae(baseline,repeat)
        proof.data['repeat_mae']=noise;proof.write()
        for role,(filename,needle,replacement) in probes.items():
            source=SHADERS/filename;original=originals[role];edited=original.replace(needle,replacement);owned=original
            record=dict(source=source.relative_to(ROOT).as_posix(),source_original_sha256=hashlib.sha256(original).hexdigest(),source_changed_sha256=hashlib.sha256(edited).hexdigest(),assignment_before=needle.decode(),assignment_changed=replacement.decode())
            proof.data['probes'][role]=record;proof.write()
            require(source.read_bytes()==original,'Concurrent source edit preserved before probe: '+role)
            try:
                offset=LOG.stat().st_size;record['changed_log_offset']=offset;proof.write()
                source.write_bytes(edited);owned=edited
                record['changed_log']=wait_reload(offset);proof.write()
                proof.capture(role+'-Changed')
            finally:
                require(source.read_bytes()==owned,'Concurrent source edit preserved; inspect before recovery: '+role)
                if owned!=original:
                    offset=LOG.stat().st_size;record['restored_log_offset']=offset
                    source.write_bytes(original);owned=original
                    record['source_restored_sha256']=sha(source);proof.write()
                    record['restored_log']=wait_reload(offset);proof.write()
            require(source.read_bytes()==original,'Exact original source bytes not restored: '+role)
            restored=proof.capture(role+'-Restored');delta=mae(baseline,proof.data['captures'][role+'-Changed']);recovery=mae(baseline,restored)
            record.update(changed_mae=delta,restored_mae=recovery,repeat_mae=noise,signal_threshold=max(.1,2*noise),restoration_tolerance=max(1,3*noise,delta*.25));proof.write()
            require(record['source_original_sha256']==record['source_restored_sha256'],'Source restoration hash differs')
            require(delta>record['signal_threshold'],'Rendered '+role+' source change does not exceed measured repeat noise')
            require(recovery<record['restoration_tolerance'],'Rendered '+role+' restoration exceeds measured tolerance')
        require(all((SHADERS/PROBES[role][0]).read_bytes()==original for role,original in originals.items()),'Final shader bytes differ from opening snapshot')
        require(len(proof.data['captures'])==2+2*len(probes),'Expected baseline/repeat plus two captures per selected source')
        proof.data.update(status='passed',passed=True,capture_count=len(proof.data['captures']));proof.write()
        print(json.dumps(dict(evidence=str(proof.path),passed=True,captures=len(proof.data['captures'])),indent=2))
    except Exception:
        proof.data.update(status='failed',passed=False,failure=traceback.format_exc())
        proof.data['current_source_sha256']={role:sha(SHADERS/PROBES[role][0]) for role in probes}
        proof.write();raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix',default='OpalLayered-Reload',help='Fresh owned output prefix; existing evidence is never overwritten')
    args=parser.parse_args()
    main(prefix=args.prefix)
