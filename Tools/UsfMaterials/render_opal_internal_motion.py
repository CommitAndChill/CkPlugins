"""Capture a fixed-view native light sweep; no material animation or image synthesis."""
from pathlib import Path
import sys,json,math,hashlib
sys.dont_write_bytecode=True
from opal_internal_command import submit
from capture_opal_internal import validate_response,source_hashes

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'

def main():
    receipt=OUT/'OpalInternal-LightSweep.json'
    if receipt.exists():raise RuntimeError('Preserve previous light sweep')
    preset_path=Path(__file__).with_name('opal_internal_preset.json')
    preset=json.loads(preset_path.read_text())
    for key in ['name','schema_version']:preset.pop(key)
    count=48
    for i in range(count):
        if (OUT/('OpalInternal-Sweep-%03d.png'%i)).exists():raise RuntimeError('Preserve existing sweep frame')
    record=dict(status='running',passed=False,frames=[],source_hashes=source_hashes(),
        preset_sha256=hashlib.sha256(preset_path.read_bytes()).hexdigest(),
        description='Fixed camera, mesh and material; only the first actual Point light changes position. Native primary viewport frames.',
        fixed_controls=preset)
    def save():receipt.write_text(json.dumps(record,indent=2))
    save()
    identity=None
    try:
        for i in range(count):
            angle=math.radians(-65+130*i/(count-1))
            controls=dict(preset)
            controls.update(subject='opal',name='OpalInternal-Sweep-%03d.png'%i,
                intensities=[7,.4,.6],source_radii=[.45,.12,.5],source_lengths=[2,0,2],
                light_positions=[[18*math.cos(angle),18*math.sin(angle),15],[12,15,12],[-4,5,14]],
                sky=.18,environment_intensity=10,reflection_brightness=.6,settle_frames=64)
            response=submit('capture_primary',**controls)
            path=OUT/controls['name'];validate_response(response,path)
            state=response['state']
            current=dict(session=response['session_id'],pid=response['pid'],looks=state['looks'],actors=state['actors'],camera=response['primary_camera_state'])
            if identity is None:identity=current
            elif current!=identity:raise RuntimeError('Material/actor/camera state changed during light-only sweep')
            if source_hashes()!=record['source_hashes']:raise RuntimeError('Shader source changed during sweep')
            record['frames'].append(dict(index=i,light_position=controls['light_positions'][0],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),response=response));save()
            print('Captured native light-sweep frame %d/%d'%(i+1,count),flush=True)
        record.update(status='passed',passed=True,frame_count=count);save()
    except Exception as error:
        record.update(status='failed',failure=str(error));save();raise

if __name__=='__main__':main()
