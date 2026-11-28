"""Build a review page exclusively from hash-verified actual Unreal proof captures."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'


def main():
    proof_path = OUTPUT / 'TailLamp-RenderedProof.json'
    proof = json.loads(proof_path.read_text(encoding='utf-8'))
    if not proof['passed'] or not proof['restored'] or proof['cleanup_errors']:
        raise RuntimeError('Only a passed, restored optical proof may feed this gallery')
    for record in proof['captures'].values():
        path = OUTPUT / record['file']
        if path.parent != OUTPUT or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise RuntimeError('Capture hash/path differs')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('Existing ffmpeg executable is required for the motion preview')
    videos = {}
    for name, fps, count in [('LightOrbit', 8, 24), ('CameraOrbit', 6, 12)]:
        fingerprint = hashlib.sha256(''.join(proof['captures'][name + '%02d' % index]['sha256'] for index in range(count)).encode()).hexdigest()[:12]
        filename = 'TailLamp-' + name + '-' + fingerprint + '.mp4'
        path = OUTPUT / filename
        if not path.exists():
            subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-framerate', str(fps),
                            '-i', str(OUTPUT / (proof['captures'][name + '00']['file'].removesuffix('00.png') + '%02d.png')), '-frames:v', str(count),
                            '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)], check=True)
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(path), '-f', 'null', '-'], check=True)
        videos[name] = filename
    def image(label, caption):
        return '<figure><a href="' + proof['captures'][label]['file'] + '"><img loading="lazy" src="' + proof['captures'][label]['file'] + '" alt="' + html.escape(caption) + '"></a><figcaption>' + html.escape(caption) + '</figcaption></figure>'
    lens = proof['initial']['looks']['OpticalTailLampLens']
    content = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CkUsf · Optical tail light</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#111318;color:#e9e9eb;font:16px/1.6 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:48px 28px}h1{font-size:clamp(32px,4vw,56px);line-height:1.12;margin:12px 0}h2{font-size:25px;margin-top:48px}p{max-width:1000px;color:#bbbfc9}small,.eyebrow{color:#d19b79}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}figure{margin:0;background:#1a1d24;border:1px solid #30343d;border-radius:12px;overflow:hidden}img,video{width:100%;display:block}figcaption{padding:13px 18px;color:#c7cbd4}a{color:#e9b991}.hero{margin-top:28px}.limits{border-left:3px solid #bc856b;padding-left:18px}code{color:#e3bfa6}@media(max-width:780px){.grid{grid-template-columns:1fr}main{padding:24px 16px}}
</style><main><div class="eyebrow">CkUsf / Native optical showcase / Actual Unreal renders</div>
<h1>A red lens.<br>A visible interior.</h1>
<p>One transmitting native Substrate Slab over separately modeled reflector cups, six LED chips, packages, housing, gasket and fasteners. Original texture-backed tooling profiles and all numeric material controls remain editable through <code>.ush</code>.</p>
<div class="hero">'''
    content += image('IorOneBaseline', 'Actual Unreal capture · broad studio fill reveals the molded transmitting cover over recessed reflectors and LED emitters') + '</div>'
    content += '<h2>Inspect the optics in motion</h2><p>Moving light reveals surface reflections; the camera sweep reveals the real separation between the lens and interior. These capture sequences are visual evidence, not frame-rate measurements.</p><div class="grid">'
    for key, caption in [('LightOrbit', 'One light orbiting the assembly'), ('CameraOrbit', 'Camera sweep across the lens and interior')]:
        content += '<figure><video controls loop muted playsinline preload="metadata" src="' + videos[key] + '" poster="' + proof['captures']['Final']['file'] + '"></video><figcaption>' + caption + '</figcaption></figure>'
    content += '</div><h2>Outer lens and interior</h2><div class="grid">'
    for key, caption in [('Final', 'Main studio lighting · restored material defaults'), ('LightsOn', 'Low-light assay · LED emission on'), ('LightsOff', 'Same low-light conditions · LED emission off'), ('Interior', 'Lens hidden · actual separate reflector and LED geometry'), ('Neutral', 'Same lens and interior · nearly neutral absorption'), ('Macro', 'Close inspection · molded lens pattern and interior separation'), ('Front', 'Front view · same material and assembly')]:
        content += image(key, caption)
    content += '</div><h2>Independent optical controls</h2><p>Calibration distance stays fixed while specimen thickness changes. Roughness, dielectric IOR and native pixel-normal distortion strength are separate live controls.</p><div class="grid">'
    for key, caption in [('Thin', '0.06 cm optical thickness'), ('Thick', '0.65 cm optical thickness'), ('Rough', 'Roughened lens'), ('NormalFlat', 'Pattern normal removed'), ('IorOneBaseline', 'Broad-fill diagnostic · dielectric IOR 1.49'), ('IorOne', 'Same broad-fill lighting · IOR 1 removes dielectric reflection')]:
        content += image(key, caption)
    content += '</div><h2>Live source edit and recovery</h2><p>Same editor, master, native front node, MID and texture bindings throughout. Both an entrypoint edit and a shared-helper edit were restored byte for byte.</p><div class="grid">'
    for key, caption in [('SourceEdit0', 'Lens .ush edit · strong absorption'), ('SourceRecovery0', 'Original lens source recovered'), ('SourceEdit1', 'Shared optical helper edit · neutral transmission'), ('SourceRecovery1', 'Original shared helper recovered')]:
        content += image(key, caption)
    content += '</div><h2>What is established</h2><p>Native colored transmission, a SimpleVolume Slab, independent MFP calibration and surface thickness, forward surface lighting, dielectric IOR-derived F0 and native Pixel Normal Offset refraction. The loaded native lens reports ' + str(lens['compiled']['closure_count']) + ' compiled closure.</p>'
    content += '<p class="limits">The lens is one outward-facing optical sheet with authored wall thickness. Native Pixel Normal Offset refracts its texture-normal pattern relative to vertex normals; it does not trace smooth geometric lens bending or entry/exit interfaces. Screen-space foreground/offscreen limitations remain. No caustics, retroreflective photometry or measured production-lens accuracy are established. The generated concept sheet was an artistic target, not an engine render.</p>'
    content += '<p><a href="TailLamp-RenderedProof.json">Rendered proof and exact hashes</a> · <a href="TailLamp-Preparation.json">Asset preparation receipt</a> · <a href="Adaptive-BSDF-Gallery.html">Adaptive materials</a></p></main></html>'
    destination = OUTPUT / 'Optical-TailLamp-Gallery.html'
    destination.write_text(content, encoding='utf-8')
    receipt = dict(proof_sha256=hashlib.sha256(proof_path.read_bytes()).hexdigest(), gallery_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), videos={key: dict(file=value, sha256=hashlib.sha256((OUTPUT / value).read_bytes()).hexdigest()) for key, value in videos.items()}, video_full_decode_passed=True)
    (OUTPUT / 'TailLamp-GalleryInspection.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    main()
