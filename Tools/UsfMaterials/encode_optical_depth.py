"""Encode already-recorded native frames; verify metadata and decode every frame."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'

def main():
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise RuntimeError('Existing ffmpeg and ffprobe required')
    motion=json.loads((OUT/'OpticalDepth-MotionProof.json').read_text())
    result={}
    for subject in ['opal','display']:
        title=subject.title();frames=motion[subject]['frames']
        assert len(frames)==24
        for index,record in enumerate(frames):
            source=OUT/f'OpticalDepth-{title}-Motion-{index:03d}.png'
            assert Path(record['capture']).resolve()==source.resolve()
            assert hashlib.sha256(source.read_bytes()).hexdigest()==record['sha256']
        target=OUT/f'OpticalDepth-{title}-Motion.mp4'
        subprocess.run([ffmpeg,'-v','error','-y','-framerate','8','-i',str(OUT/f'OpticalDepth-{title}-Motion-%03d.png'),
                        '-frames:v','24','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
        metadata=json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-select_streams','v:0',
                        '-show_entries','stream=codec_name,width,height,nb_read_frames,duration','-of','json',str(target)],text=True))['streams'][0]
        assert metadata['codec_name']=='h264' and metadata['width']==1600 and metadata['height']==1200
        assert int(metadata['nb_read_frames'])==24 and abs(float(metadata['duration'])-3)<.001
        subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
        result[subject]=dict(file=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                            **metadata,all_frames_decode_verified=True,fps=8,source='24 actual native Unreal captures')
    (OUT/'OpticalDepth-EncodedMotion.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
