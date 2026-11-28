"""Record the current three-surface study without changing shader source or assets."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import subprocess
from opal_depth_command import submit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Saved/UsfMaterialGallery'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = OUT/'OpalDepth-StudyRecord.json'
    if receipt.exists():
        raise RuntimeError('Preserve existing depth study record')
    data = dict(status='running', visual_acceptance=False, captures=[], frames=[],
        scope='Construction study; irregular opal fire and mockup fidelity remain unfinished.',
        limitations=['Thin-surface transmission, no traced entry/exit or spectral diffraction.',
                     'The middle surface still contributes an extra continuous grazing rim.',
                     'Native fine glints are disabled; this study evaluates geometric depth.'])

    def write():
        receipt.write_text(json.dumps(data, indent=2)+'\n')

    def capture(name, **controls):
        result = submit('capture', name=name, subject='opal',
                        visible=controls.pop('visible', dict(Core=True, Shell=True, FireLayer=True)),
                        settle_frames=64, **controls)
        result['sha256'] = sha(Path(result['capture']))
        data['captures'].append(result)
        write()
        if result.get('capture_backend') != 'AutomationLibrary.take_high_res_screenshot primary editor viewport' or not result.get('native_task_done'):
            raise RuntimeError('Native primary capture required')
        for look in result['state']['looks'].values():
            if not look['compiled']['valid'] or look['compiled']['compile_errors']:
                raise RuntimeError('Native shader compilation incomplete')
        print(name, flush=True)
        return result

    write()
    try:
        for name, controls in [
            ('OpalDepth-CurrentStudy.png', {}),
            ('OpalDepth-Study-ExteriorOnly.png', dict(visible=dict(Core=False, Shell=True, FireLayer=False))),
            ('OpalDepth-Study-CoreOnly.png', dict(visible=dict(Core=True, Shell=False, FireLayer=False))),
            ('OpalDepth-Study-MiddleOff.png', dict(visible=dict(Core=True, Shell=True, FireLayer=False))),
            ('OpalDepth-Study-SecondAngle.png', dict(camera=[19, -18, 12]))]:
            capture(name, **controls)
        radius = math.hypot(24, 11)
        base_angle = math.atan2(-11, 24)
        for index in range(16):
            angle = base_angle+math.radians(8)*math.sin(2*math.pi*index/16)
            record = capture('OpalDepth-StudyMotion-%03d.png' % index,
                             camera=[radius*math.cos(angle), radius*math.sin(angle), 14])
            data['frames'].append(dict(file=Path(record['capture']).name, sha256=record['sha256']))
            write()
        ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
        if not ffmpeg or not ffprobe:
            raise RuntimeError('Existing ffmpeg/ffprobe required')
        video = OUT/'OpalDepth-StudyMotion.mp4'
        subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-n', '-framerate', '6', '-i',
                        str(OUT/'OpalDepth-StudyMotion-%03d.png'), '-frames:v', '16', '-an',
                        '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)], check=True)
        stream = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-count_frames',
            '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,width,height,nb_read_frames,r_frame_rate',
            '-of', 'json', str(video)], text=True))['streams'][0]
        if (stream['width'], stream['height'], int(stream['nb_read_frames']), stream['r_frame_rate']) != (1600,1200,16,'6/1'):
            raise RuntimeError('Encoded study frame contract differs')
        subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-i', str(video), '-f', 'null', '-'], check=True)
        data['video'] = dict(file=video.name, sha256=sha(video), all_frames_decode_verified=True, **stream)
        data['sources'] = {name:sha(ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'/name)
                           for name in ['OpticalOpalCore.ush','OpticalOpalShell.ush','OpticalOpalFireLayer.ush']}
        protected = json.loads((OUT/'OpalGlints-ProtectedBaseline.json').read_text())['files']
        differences = [name for name, digest in protected.items() if sha(ROOT/name) != digest]
        data['protected'] = dict(count=len(protected), differences=differences)
        if differences:
            raise RuntimeError('Protected prior artifacts differ')
        data['status'] = 'recorded'
        write()
    except Exception as error:
        data.update(status='failed', failure=str(error))
        write()
        raise


if __name__ == '__main__':
    main()
