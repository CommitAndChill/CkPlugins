"""Build the additive Opal three-layer gallery after final native evidence exists.

Explicit main only; no Unreal calls, asset changes, image edits or launches.
"""
from pathlib import Path
import hashlib
import html
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Saved/UsfMaterialGallery'
DEST = OUT/'Opal-Three-Layer-Gallery.html'
MASTER = '/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_OpticalOpalInternal.M_CkUsf_Look_OpticalOpalInternal'
BACKEND = 'AutomationLibrary.take_high_res_screenshot primary editor viewport'
ORIGINAL = ROOT/'Plugins/CkTests/Resources/CkUsf/OpalPolishV2/Source/OpalOriginal.png'
ORIGINAL_SHA = '7d66d3ff5ca042e4ffa170eeb844f18aaac921a4bba2d591030b2d41b59660b6'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    path = OUT/name
    require(path.is_file(), 'Missing final evidence: '+name)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def native(response):
    require(response.get('ok') is True and response.get('capture_backend') == BACKEND and
            response.get('native_task_done') is True and response.get('native_task_valid') is True,
            'Completed native primary screenshot required')
    state = response['state']
    require(set(state['looks']) == set(state['actors']) == {'Opal'}, 'One subject actor/material required')
    look = state['looks']['Opal']
    stats = look['compiled']
    require(look['master'] == MASTER and stats['valid'] and stats['closure_count'] == 3 and
            not stats['compile_errors'] and not stats['has_glint'] and not stats['complex_special'],
            'Exact compiled three-layer material required')
    actor = state['actors']['Opal']
    require(actor['mesh'] == '/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body.SM_AmberHero_Body', 'Approved single Body mesh required')
    require(actor['assigned_material'] == look['mid'] and
            all(abs(v) < 1e-5 for v in actor['position']) and
            all(abs(v-1) < 1e-5 for v in actor['scale']) and
            all(abs(v) < 1e-5 for v in actor['rotation'].values()), 'Single identity Body assignment required')
    path = Path(response['capture'])
    require(path.resolve().parent == OUT.resolve() and path.is_file(), 'Owned native PNG required')
    with Image.open(path) as image:
        require(image.format == 'PNG' and image.size == (1600, 1200), 'Native 1600x1200 PNG required')
        image.load()
    require(response['primary_camera_state'] == state['primary_camera_state'], 'Actual camera sampling required')
    return state


def capture(stem):
    receipt = read(stem+'.json')
    require(receipt.get('passed') is True and receipt.get('status') == 'passed', 'Capture receipt must pass: '+stem)
    state = native(receipt['response'])
    path = OUT/(stem+'.png')
    require(Path(receipt['response']['capture']).resolve() == path.resolve() and sha(path) == receipt['capture_sha256'],
            'Capture hash/path mismatch: '+stem)
    require(receipt['source_hashes'] == receipt['source_hashes_after'], 'Source changed during capture: '+stem)
    return receipt, state


def material(state):
    look = state['looks']['Opal']
    return {key:look[key] for key in ['master', 'textures', 'scalars', 'vectors']}


def stable_motion(state):
    # Actor/primary-camera identities are retained across the entire actual sweep.
    rig = json.loads(json.dumps(state['rig']))
    for light in rig['lights']:
        light.pop('position')
    return dict(material=material(state), actors=state['actors'], primary=state['primary_camera_state'], rig=rig)


def main():
    require(not DEST.exists(), 'Preserve existing gallery; this builder writes only a new gallery')
    final, state = capture('OpalInternal-Final')
    require(state['looks']['Opal'].get('source_instance') == '/CkFoundation/CkUsf/Instances/Optical/MI_OpticalOpalInternal.MI_OpticalOpalInternal',
            'Final reusable saved material instance required')
    for relative, digest in final['source_hashes'].items():
        path = (ROOT/relative).resolve()
        require(path.is_relative_to(ROOT.resolve()) and path.is_file() and sha(path) == digest,
                'Final source/dependency pin differs: '+relative)
    require(abs(state['looks']['Opal']['scalars']['CoatThicknessCm']-.03)<1e-5, 'Gallery clear polish thickness differs from final material')
    instance = read('OpalInternal-InstancePreparation.json')
    require(instance['source_instance'] == state['looks']['Opal']['source_instance'] and instance['preset_sha256'] == state['looks']['Opal']['preset_sha256'] and instance['parent'] == MASTER, 'Final saved-instance evidence differs')
    controls = []
    for suffix, label in [('NoFlash', 'Internal reflection strength set to zero'), ('LightsOff', 'Lights and environment turned off'),
                          ('LowCoat', 'Outer polish IOR reduced to 1.01'), ('BodyTransmission', 'Increased body transmission')]:
        stem = 'OpalInternal-Final-'+suffix
        if suffix == 'BodyTransmission' and not (OUT/(stem+'.json')).exists():
            continue
        receipt, diagnostic = capture(stem)
        require(receipt['source_hashes'] == final['source_hashes'], 'Control uses a different material source')
        controls.append((stem, label, diagnostic['looks']['Opal']['scalars'], diagnostic['looks']['Opal']['vectors']))

    proof = read('OpalInternal-Reload-Final-Proof.json')
    require(proof.get('passed') is True and proof.get('status') == 'passed' and len(proof['captures']) == 4,
            'Complete final live-reload proof required')
    for record in proof['captures'].values():
        native(record)
        require(sha(Path(record['capture'])) == record['sha256'], 'Reload PNG hash differs')
    for probe in proof['probes'].values():
        source = (ROOT/probe['source']).resolve()
        require(source.is_relative_to(ROOT.resolve()) and sha(source) == probe['source_original_sha256'] == probe['source_restored_sha256'],
                'Final live-reload source not restored exactly')

    sweep = read('OpalInternal-LightSweep.json')
    require(sweep.get('passed') is True and sweep.get('status') == 'passed' and
            sweep.get('frame_count') == len(sweep['frames']) == 48, 'Complete 48-frame moving-light evidence required')
    require(sweep['source_hashes'] == final['source_hashes'], 'Motion and final still source pins differ')
    first = None
    positions = []
    for index, frame in enumerate(sweep['frames']):
        response = frame['response']
        motion = native(response)
        require(frame['index'] == index and sha(Path(response['capture'])) == frame['sha256'], 'Motion frame hash/order differs')
        current = stable_motion(motion)
        if first is None:
            first = current
            session = (response['pid'], response['session_id'])
            other_positions = [light['position'] for light in motion['rig']['lights'][1:]]
        require(current == first and (response['pid'], response['session_id']) == session and
                [light['position'] for light in motion['rig']['lights'][1:]] == other_positions,
                'Motion changed more than the first actual point-light position')
        require(material(motion) == material(state), 'Motion and final still material controls differ')
        positions.append(tuple(motion['rig']['lights'][0]['position']))
    require(len(set(positions)) > 1, 'Point light did not move')
    video = OUT/'OpalInternal-LightSweep.mp4'
    require(video.is_file() and video.stat().st_size > 32, 'Encoded moving-light video required')
    header = video.read_bytes()[:64]
    require(b'ftyp' in header, 'Expected MP4 container')
    require(sha(ORIGINAL) == ORIGINAL_SHA, 'Preserved original artwork changed')
    import os
    original_link = Path(os.path.relpath(ORIGINAL, OUT)).as_posix()
    h = html.escape
    cards = ''.join('<figure><a href="'+stem+'.png"><img loading="lazy" src="'+stem+'.png" alt="'+label+'"></a><figcaption>'+label+
        ' · <a href="'+stem+'.json">native receipt</a></figcaption></figure>' for stem, label, _, _ in controls)
    presets = h(json.dumps(dict(scalars=state['looks']['Opal']['scalars'], vectors=state['looks']['Opal']['vectors']), indent=2))
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Opal — three native layers</title><style>
:root{color-scheme:dark;font:16px/1.6 system-ui,sans-serif;background:#101317;color:#e8edf0}body{max-width:1160px;margin:auto;padding:44px 24px}h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.1;font-weight:550;margin:12px 0}h2{font-weight:500}p{max-width:780px;color:#b9c4cc}a{color:#a2d8e5}img,video{display:block;width:100%;height:auto;border-radius:12px;background:#080a0c}figure{margin:24px 0}figcaption{font-size:.88rem;color:#a1afb9;margin:8px 0}video{max-height:760px}.eyebrow{letter-spacing:.14em;text-transform:uppercase;font-size:.76rem;color:#99bdc9}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:22px}.source{max-width:180px}details{border-top:1px solid #303a42;padding:20px 0;margin-top:28px}summary{cursor:pointer}pre{overflow:auto;background:#171d22;padding:20px;border-radius:10px;font-size:.8rem}.note{font-size:.9rem;color:#98a8b4}footer{border-top:1px solid #303a42;margin-top:36px;padding-top:20px}
</style><body><div class="eyebrow">Native material study · one mesh</div><h1>Opal, in three layers</h1>
<p>A clear polish layer, colored internal reflections and a quiet cloudy body, combined in one material on one mesh. The clear polish is authored at 0.3 mm; no separate shell geometry is used.</p>
<figure><a href="OpalInternal-Final.png"><img width="1600" height="1200" src="OpalInternal-Final.png" alt="Final native three-layer opal render"></a><figcaption>Final native render · 1600 × 1200 · <a href="OpalInternal-Final.json">capture receipt</a></figcaption></figure>
<h2>Light across the interior</h2><video controls autoplay loop muted playsinline preload="metadata" poster="OpalInternal-Final.png"><source src="OpalInternal-LightSweep.mp4" type="video/mp4"></video>
<p class="note">The camera, mesh and material stay fixed. Only the first actual point light moves; the remaining lights and environment stay fixed. The loop contains 48 native frames over four seconds.</p>
<details><summary>Material controls and comparison captures</summary><p>These captures record selected material and lighting controls. Their receipts contain the actual settings; perceived changes remain a visual review.</p><div class="grid">'''+cards+'''</div><pre>'''+presets+'''</pre></details>
<details><summary>Artwork and native evidence</summary><p>The earlier selected color artwork is preserved exactly. New numerical orientation data supplies full-area internal reflection potential; no new color artwork or post-render color treatment was added.</p><a href="'''+h(original_link, quote=True)+'''"><img class="source" src="'''+h(original_link, quote=True)+'''" alt="Preserved original opal color artwork"></a><p><a href="OpalInternal-Reload-Final-Proof.json">Final source-reload proof</a> · <a href="OpalInternal-LightSweep.json">Moving-light frame evidence</a> · <a href="OpalInternal-InstancePreparation.json">Saved material instance</a></p><p class="note">MP4 SHA256: '''+sha(video)+'''</p></details>
<footer><p class="note">An authored optical approximation using three native material layers. Perceived depth and the visual match to real opal remain under review. This is not measured diffraction or volumetric transport evidence.</p></footer></body></html>'''
    with DEST.open('x', encoding='utf-8') as stream:
        stream.write(document)
    print(DEST)


if __name__ == '__main__':
    main()
