"""Build the refined review page from verified actual Unreal captures only."""
from pathlib import Path
import hashlib
import html
from html.parser import HTMLParser
import json
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
REQUIRED = {'Original', 'Refined', 'OriginalRecovered', 'Front', 'Opposite', 'Macro',
            'Interior', 'LedOff', 'LedOn', 'Rough', 'Flat', 'SourceEdit',
            'SourceRecovered', 'HelperEdit', 'HelperRecovered', 'Final'}
REQUIRED |= {'LightOrbit%02d' % i for i in range(24)}
REQUIRED |= {'CameraOrbit%02d' % i for i in range(12)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def motion(ffmpeg, captures, name, count, fps):
    records = [captures[name + '%02d' % i] for i in range(count)]
    signature = json.dumps(dict(frames=[r['sha256'] for r in records], fps=fps,
                                codec='libx264', crf=18, pixels='yuv420p'), sort_keys=True)
    fingerprint = hashlib.sha256(signature.encode()).hexdigest()[:16]
    destination = OUTPUT / ('TailLamp-Refined-' + name + '-' + fingerprint + '.mp4')
    if not destination.exists():
        # Explicit file list: proof filenames need not form a numbered sequence.
        listing = ''.join("file '" + (OUTPUT / r['file']).as_posix().replace("'", "'\\''") + "'\n" for r in records)
        # Keep the reproducible concat input inside the selected workspace. The
        # managed Windows temporary directory may not permit child file writes.
        sequence = OUTPUT / ('TailLamp-Refined-' + name + '-' + fingerprint + '.ffconcat')
        if sequence.exists() and sequence.read_text(encoding='utf-8') != listing:
            raise RuntimeError('Preserve differing encoding input: ' + str(sequence))
        if not sequence.exists():
            sequence.write_text(listing, encoding='utf-8')
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-xerror', '-n',
                        '-r', str(fps), '-f', 'concat', '-safe', '0', '-i', str(sequence),
                        '-frames:v', str(count), '-an', '-c:v', 'libx264', '-crf', '18',
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination)], check=True)
    decoded = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-xerror',
                              '-i', str(destination), '-map', '0:v:0', '-an', '-progress', 'pipe:1',
                              '-f', 'null', '-'], check=True, capture_output=True, text=True)
    frames = [int(line.split('=', 1)[1].strip()) for line in decoded.stdout.splitlines() if line.startswith('frame=')]
    if not frames or frames[-1] != count:
        raise RuntimeError('Motion decode frame count differs: ' + name)
    return dict(file=destination.name, sha256=digest(destination), frames=count, fps=fps,
                input_sha256=[r['sha256'] for r in records], full_decode_passed=True)


def main():
    proof_path = OUTPUT / 'TailLamp-RefinedProof.json'
    proof = json.loads(proof_path.read_text(encoding='utf-8'))
    if proof.get('passed') is not True or proof.get('restored') is not True or proof.get('cleanup_errors') != []:
        raise RuntimeError('Only a passed, restored proof without cleanup errors may feed this gallery')
    captures = proof['captures']
    if REQUIRED - set(captures):
        raise RuntimeError('Missing proof captures: ' + ', '.join(sorted(REQUIRED - set(captures))))
    for label, record in captures.items():
        relative = Path(record['file'])
        path = (OUTPUT / relative).resolve()
        if relative.is_absolute() or path.parent != OUTPUT.resolve() or path.suffix.lower() != '.png' or digest(path) != record['sha256']:
            raise RuntimeError('Capture hash/path differs: ' + label)
        if not isinstance(record['state'], dict):
            raise RuntimeError('Capture state missing: ' + label)
    if not proof['sources']:
        raise RuntimeError('Source recovery hashes are required')
    for relative, record in proof['sources'].items():
        path = (ROOT / relative).resolve()
        expected = record if isinstance(record, str) else record['sha256']
        if Path(relative).is_absolute() or not path.is_relative_to(ROOT.resolve()) or digest(path) != expected:
            raise RuntimeError('Current source hash/path differs: ' + relative)
    original_rig = captures['Original']['state'].get('rig')
    if not original_rig or original_rig != captures['Refined']['state'].get('rig'):
        raise RuntimeError('Original/refined comparison rig differs or is missing')
    lens = captures['Final']['state']['looks']['OpticalTailLampLens']
    compiled = lens['compiled']
    if not compiled['valid'] or compiled['closure_count'] != 1 or compiled['compile_errors']:
        raise RuntimeError('Final refined lens must have one valid native closure without compile errors')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('Existing ffmpeg executable is required')
    videos = {name: motion(ffmpeg, captures, name, count, fps)
              for name, count, fps in [('LightOrbit', 24, 8), ('CameraOrbit', 12, 6)]}
    def esc(value):
        return html.escape(str(value), quote=True)
    def image(label, caption):
        filename = esc(captures[label]['file'])
        return '<figure><a href="' + filename + '"><img loading="lazy" src="' + filename + '" alt="' + esc(caption) + '"></a><figcaption>' + esc(caption) + '</figcaption></figure>'
    content = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CkUsf · Refined optical tail light</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#111318;color:#e9e9eb;font:16px/1.6 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:48px 28px}h1{font-size:clamp(32px,4vw,56px);line-height:1.12;margin:12px 0}h2{font-size:25px;margin-top:48px}p{max-width:1000px;color:#bbbfc9}small,.eyebrow{color:#d19b79}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}figure{margin:0;background:#1a1d24;border:1px solid #30343d;border-radius:12px;overflow:hidden}img,video{width:100%;display:block}figcaption{padding:13px 18px;color:#c7cbd4}a{color:#e9b991}.hero{margin-top:28px}.limits{border-left:3px solid #bc856b;padding-left:18px}code{color:#e3bfa6}@media(max-width:780px){.grid{grid-template-columns:1fr}main{padding:24px 16px}}
</style><main><div class="eyebrow">CkUsf / Refined optical showcase / Actual Unreal renders</div>
<h1>Molded detail.<br>A clearer interior.</h1>
<p>Original analytical tooling textures define three optical fields and a continuous molded perimeter. Calmer reflector and housing finishes refine the same assembly geometry, with one native optical closure over the separate interior.</p><div class="hero">'''
    content += image('Final', 'Refined finish · final restored Unreal capture') + '</div>'
    content += '<h2>Original and refined</h2><p>The original and refined finishes use identical recorded studio rig settings. Both images come from the actual Unreal capture session.</p><div class="grid">'
    content += image('Original', 'Original · uniform flute field and original hardware finishes')
    content += image('Refined', 'Refined · distinct optical fields, smooth perimeter and calmer hardware finishes')
    content += '</div><h2>Inspect the optics in motion</h2><p>Actual capture sequences: 24 light positions at 8 fps and 12 camera positions at 6 fps. Playback demonstrates changing views and illumination; it is not a performance measurement.</p><div class="grid">'
    for name, caption in [('LightOrbit', 'Refined finish · moving light'), ('CameraOrbit', 'Refined finish · camera sweep')]:
        content += '<figure><video controls loop muted playsinline preload="metadata" src="' + esc(videos[name]['file']) + '" poster="' + esc(captures['Final']['file']) + '"></video><figcaption>' + caption + '</figcaption></figure>'
    content += '</div><h2>Cover and interior</h2><div class="grid">'
    for label, caption in [('Front', 'Front view · optical field layout'), ('Opposite', 'Opposite view · cover and interior depth'), ('Macro', 'Close inspection · molded tooling and perimeter'), ('Interior', 'Lens hidden · separate reflector cups and six emitter packages')]:
        content += image(label, caption)
    content += '</div><h2>LED and surface assays</h2><p>The roughness and LED endpoints are clearly measurable. Flattening the shallow tooling normal changes the image by about0.0041 mean display RGB, close to the0.0033 comparison noise level; this is a subtle visual control rather than a decisive isolated normal-response proof.</p><div class="grid">'
    for label, caption in [('LedOff', 'LED assay · emission off'), ('LedOn', 'LED assay · emission on'), ('Rough', 'Surface assay · roughened lens'), ('Flat', 'Surface assay · tooling normal flattened')]:
        content += image(label, caption)
    content += '</div><h2>Live source edits and recovery</h2><p>Entrypoint and shared optical helper edits were captured in Unreal, followed by exact byte recovery. Rendered recovery differences are0.0179/0.0167 mean display RGB within the declared0.025 bound, rather than noise-floor pixel agreement. Current source hashes are checked against the passed proof before this page is generated.</p><div class="grid">'
    for label, caption in [('SourceEdit', 'Live lens entrypoint edit'), ('SourceRecovered', 'Lens entrypoint source recovered'), ('HelperEdit', 'Live shared optical helper edit'), ('HelperRecovered', 'Shared optical helper source recovered'), ('OriginalRecovered', 'Original finish recovered after variant comparison'), ('Final', 'Refined finish · final restored state')]:
        content += image(label, caption)
    content += '</div><h2>Evidence and limits</h2><p>The final lens reports one valid compiled closure without compile errors. The proof records capture states, recovery hashes and assay metrics.</p>'
    content += '<p class="limits">The cover remains one exterior optical sheet with authored material thickness. Analytical normal and thickness maps describe tooling; they do not establish geometric prism tracing, caustics, certified photometry or production-lens accuracy. Native screen-space refraction retains foreground and offscreen limitations. Browser layout inspection is blocked by policy and has not been performed.</p>'
    content += '<p><a href="Optical-TailLamp-Gallery.html">Original optical gallery</a> · <a href="TailLamp-RefinedProof.json">Refined proof and exact hashes</a> · <a href="TailLamp-RefinedPreparation.json">Refined preparation receipt</a> · <a href="TailLamp-RefinedGalleryInspection.json">Gallery inspection receipt</a></p></main></html>'
    destination = OUTPUT / 'Optical-TailLamp-Refined-Gallery.html'
    destination.write_text(content, encoding='utf-8')
    receipt = dict(proof_sha256=digest(proof_path), gallery_sha256=digest(destination),
                   capture_count=len(captures), capture_hashes_verified=True, current_source_hashes_verified=True,
                   comparison_rig_equal=True, passed=proof['passed'], restored=proof['restored'],
                   cleanup_errors=proof['cleanup_errors'], metrics=proof['metrics'], videos=videos,
                   video_full_decode_passed=True, html_local_references_verified=False,
                   browser_layout_inspection='blocked_by_policy; not performed',
                   limitations=['No browser layout inspection', 'Capture sequences are not performance evidence'])
    inspection = OUTPUT / 'TailLamp-RefinedGalleryInspection.json'
    inspection.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    class References(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.paths = set()

        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key in {'href', 'src', 'poster'} and value:
                    parsed = urlsplit(value)
                    if parsed.scheme or parsed.netloc:
                        raise RuntimeError('Unexpected nonlocal HTML reference: ' + value)
                    if parsed.path:
                        self.paths.add(unquote(parsed.path))
    references = References()
    references.feed(destination.read_text(encoding='utf-8'))
    references.close()
    for relative in sorted(references.paths):
        path = (OUTPUT / relative).resolve()
        if not path.is_relative_to(OUTPUT.resolve()) or not path.is_file():
            raise RuntimeError('Missing or unsafe gallery reference: ' + relative)
    receipt.update(html_local_references_verified=True, html_local_reference_count=len(references.paths))
    inspection.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    main()
