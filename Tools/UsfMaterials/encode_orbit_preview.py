"""Encode the proven phase-sampled native captures without interpolation or grading."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'Saved/UsfMaterialGallery'


def main():
    proof=json.loads((OUTPUT/'OrbitLight-Proof.json').read_text())
    if not proof.get('passed') or not proof.get('restored'): raise RuntimeError('Finish and restore the light proof first')
    frames={}
    for index in range(36):
        name=f'OrbitLight-Phase-{index:03d}.png'
        path=OUTPUT/name
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if proof['captures'][f'Phase-{index:03d}']['sha256']!=digest: raise RuntimeError('Source frame differs')
        frames[name]=digest
    destination=OUTPUT/'OrbitLight-Preview.mp4'
    arguments=['ffmpeg','-v','error','-n','-framerate','4','-i',str(OUTPUT/'OrbitLight-Phase-%03d.png'),
               '-frames:v','36','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(destination)]
    if destination.exists(): raise RuntimeError('Preserve the existing encoded preview before creating another')
    subprocess.run(arguments,check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_entries',
                    'stream=nb_read_frames,r_frame_rate,width,height:format=duration','-of','json',str(destination)],text=True))
    if int(probe['streams'][0]['nb_read_frames'])!=36 or abs(float(probe['format']['duration'])-9)>.001:
        raise RuntimeError('Encoded preview timing differs from the proof')
    receipt={'output_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'frame_count':36,'fps':4,
             'duration_seconds':9,'source_frame_sha256':frames,'ffprobe':probe,'arguments':arguments,
             'scope':'Native UE phase samples,10degrees/frame, encoded at4fps. This plays2x the nominal20degrees/second orbit; not real-time footage, interpolation or performance evidence.'}
    (OUTPUT/'OrbitLight-Preview.json').write_text(json.dumps(receipt,indent=2))
    print(destination)


if __name__=='__main__':main()
