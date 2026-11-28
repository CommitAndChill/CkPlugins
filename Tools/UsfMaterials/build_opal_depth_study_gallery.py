"""Build a clearly labelled construction study from completed native capture evidence."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Saved/UsfMaterialGallery'


def main():
    report = json.loads((OUT/'OpalDepth-StudyRecord.json').read_text())
    if report['status'] != 'recorded' or report['visual_acceptance']:
        raise RuntimeError('Completed construction record without inferred artistic acceptance required')
    for record in report['captures']:
        if hashlib.sha256(Path(record['capture']).read_bytes()).hexdigest() != record['sha256']:
            raise RuntimeError('Recorded native capture changed')
    if not report['video']['all_frames_decode_verified']:
        raise RuntimeError('Decoded native-motion record required')
    target = OUT/'Opal-Depth-Study.html'
    if target.exists():
        raise RuntimeError('Preserve existing gallery')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Opal · depth construction study</title><style>
*{box-sizing:border-box}body{margin:0;background:#101216;color:#ecedef;font:17px/1.55 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:44px 24px}h1{font-size:clamp(28px,4vw,46px);line-height:1.15;margin:12px 0 20px}h2{margin:34px 0 16px}p{max-width:900px;color:#bbc3cb}small,.label{color:#9aaab7}.label{letter-spacing:.13em;text-transform:uppercase;font-size:12px}figure{margin:0;border:1px solid #353b43;border-radius:12px;overflow:hidden;background:#171b20}img,video{width:100%;display:block}figcaption{padding:12px 16px;color:#c4d0da;font-size:14px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}a{color:#9fd5f3}.note{border-left:3px solid #8baac0;padding-left:18px;margin:26px 0}.target{aspect-ratio:4/3;overflow:hidden;position:relative}.target img{position:absolute;width:200%;max-width:none;right:0;top:0}@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style><main><div class="label">Actual Unreal captures · construction study</div>
<h1>A clear exterior with buried color.</h1><p>The target is a visibly thick, polished exterior enclosing the cloudy mineral body and irregular colored flashes at different depths. This study separates those surfaces in geometry and keeps all three materials editable through .ush.</p>
<div class="note"><strong>Construction is further along than the opal finish.</strong><p>The clear perimeter and transmitting middle layer are visible. The broad color pattern and additional inner glass rim still need work before this matches the concept. Fine metallic-style glitter is disabled.</p></div>
<figure><video controls loop muted playsinline preload="metadata" poster="OpalDepth-CurrentStudy.png" src="OpalDepth-StudyMotion.mp4"></video><figcaption>16 actual Unreal frames · fixed illumination, changing viewpoint. This is appearance evidence, not a real-time performance measurement.</figcaption></figure>
<h2>The three surfaces</h2><div class="grid"><figure><img src="OpalDepth-Study-ExteriorOnly.png" alt="Clear exterior in isolation"><figcaption>Exterior only · smooth polished reflection on the outer geometry.</figcaption></figure><figure><img src="OpalDepth-Study-CoreOnly.png" alt="Recessed mineral core"><figcaption>Deeper mineral core · original texture-backed color and cloudy body.</figcaption></figure></div>
<div class="grid"><figure><img src="OpalDepth-Study-MiddleOff.png" alt="Exterior and core, without the middle color layer"><figcaption>Exterior + core · middle reflections disabled.</figcaption></figure><figure><img src="OpalDepth-CurrentStudy.png" alt="All three surfaces assembled"><figcaption>All three · transmitting middle reflections preserve the deeper core.</figcaption></figure></div>
<h2>Illustrative target and current construction</h2><div class="grid"><figure><div class="target"><img src="Amber-Original-IllustrativeConcept.png" alt="Original illustrative opal target"></div><figcaption>Original illustrative concept · not an Unreal render.</figcaption></figure><figure><img src="OpalDepth-Study-SecondAngle.png" alt="Current Unreal study from another viewpoint"><figcaption>Actual Unreal study · depth and ordering remain the focus.</figcaption></figure></div>
<p><small>Separate geometry supplies real spacing between the exterior, middle surface and core. The material uses native Substrate surface transmission; it does not trace entry/exit paths or simulate spectral diffraction and mineral volume scattering. Generated texture artwork and derived data are artistic inputs, not measured optical scans. The rejected opaque-patch and broad-rainbow studies are excluded here.</small></p>
<p><a href="OpalDepth-StudyRecord.json">Capture record</a> · <a href="OpalDepth-Reload-Proof.json">Core and shell source proof, including the weak middle diagnostic</a> · <a href="OpalDepth-Reload-FireStrong-Proof.json">Stronger middle-layer source proof</a></p></main></html>'''
    for reference in re.findall(r'(?:src|href)="([^"]+)"', html):
        if not (OUT/reference).is_file():
            raise RuntimeError('Missing gallery reference: '+reference)
    target.write_text(html, encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()
