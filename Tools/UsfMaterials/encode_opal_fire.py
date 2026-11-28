"""Encode only existing hash-verified native opal frames, preserving existing videos."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise RuntimeError('Existing ffmpeg and ffprobe required')
    proof=json.loads((OUT/'OpalFire-MotionProof.json').read_text());assert proof['passed'] and proof['status']=='passed'
    frames=proof['opal']['frames'];assert len(frames)==24 and proof['opal']['frame_count']==24
    for index,record in enumerate(frames):
        path=OUT/('OpalFire-Motion-%03d.png'%index)
        assert Path(record['capture']).resolve()==path.resolve() and sha(path)==record['sha256']
    signature=json.dumps(dict(frames=[r['sha256'] for r in frames],fps=8,codec='libx264',crf=18,pix_fmt='yuv420p'),sort_keys=True)
    fingerprint=hashlib.sha256(signature.encode()).hexdigest()[:16];target=OUT/('OpalFire-Motion-'+fingerprint+'.mp4')
    listing=''.join("file '"+(OUT/('OpalFire-Motion-%03d.png'%i)).as_posix().replace("'","'\\''")+"'\n" for i in range(24));concat=OUT/('OpalFire-Motion-'+fingerprint+'.ffconcat')
    if concat.exists() and concat.read_text(encoding='utf-8')!=listing:raise RuntimeError('Preserve differing concat source')
    if not concat.exists():concat.write_text(listing,encoding='utf-8')
    if not target.exists():subprocess.run([ffmpeg,'-v','error','-xerror','-n','-r','8','-f','concat','-safe','0','-i',str(concat),'-frames:v','24','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
    metadata=json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=codec_name,width,height,nb_read_frames,duration,r_frame_rate','-of','json',str(target)],text=True))['streams'][0]
    assert metadata['codec_name']=='h264' and (metadata['width'],metadata['height'])==(1600,1200) and int(metadata['nb_read_frames'])==24 and abs(float(metadata['duration'])-3)<.001
    assert metadata['r_frame_rate']=='8/1'
    subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
    record={'opal':dict(file=target.name,sha256=sha(target),**metadata,fps=8,frame_count=24,all_frames_decode_verified=True,input_sha256=[r['sha256'] for r in frames],concat_file=concat.name)}
    path=OUT/'OpalFire-EncodedMotion.json';data=json.dumps(record,indent=2)+'\n'
    if path.exists() and path.read_text()!=data:raise RuntimeError('Preserve differing encoded-motion receipt')
    if not path.exists():path.write_text(data)
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()
