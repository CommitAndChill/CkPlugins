"""Quick actual-versus-concept visual review; never labels a concept as a render."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'


def main():
    concept = Path('C:/Users/sulfu/.codex/generated_images/01a152d9-e03c-74b0-9923-ed775a17621a/exec-db21d87c-55c5-4d44-91fc-b8516fbc1f62.png')
    reference = OUTPUT / 'Amber-Original-IllustrativeConcept.png'
    if not reference.exists():
        shutil.copyfile(concept, reference)
    old = 'AmberProof-b0328bbf8b22-Final.png'
    new = 'AmberHero-Fidelity-Final.png'
    content = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Amber · fidelity correction</title><style>
body{background:#111318;color:#e9e9eb;font:16px/1.6 system-ui;margin:0}main{max-width:1400px;margin:auto;padding:35px 24px}h1{font-size:40px;line-height:1.1}p{max-width:1000px;color:#bec1c9}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:#1d2028;border-radius:10px;overflow:hidden}img{width:100%;display:block}figcaption{padding:15px}.concept{aspect-ratio:4/3;background-image:url('Amber-Original-IllustrativeConcept.png');background-size:200% 200%;background-position:left bottom}a{color:#ebbc8b}@media(max-width:750px){.grid{grid-template-columns:1fr}}</style><main>
<h1>Amber: correcting the representation</h1><p>Astra identified a scene-authoring mismatch: an opaque rear support, a regular twig, missing inclusions and point-light dots could not reproduce the original concept. The previous technical checks did not establish visual fidelity.</p>
<div class="grid"><figure><div class="concept"></div><figcaption>Original generated illustrative target · amber panel · not an Unreal render</figcaption></figure><figure><img src="'''+new+'''" alt="Corrected actual Unreal hero"><figcaption>Corrected actual Unreal hero · no opaque backing</figcaption></figure></div>
<h2>What changed</h2><p>Closed irregular pebble geometry, a photographed masked leaf with artist-controlled thin-tissue transmission, 59 bubble surfaces and 65 suspended fragments, elongated reflection sources and a floor visible through the amber. The new leaf texture is CGBookcase Autumn Leaf31, published under CC0. All sampling and optical/shading controls remain editable through .ush.</p>
<div class="grid"><figure><img src="'''+old+'''" alt="Rejected prior plaque"><figcaption>Before · rejected opaque-backed plaque</figcaption></figure><figure><img src="'''+new+'''" alt="Corrected actual hero"><figcaption>After · transparent depth and detailed inclusions</figcaption></figure></div>
<h2>Still a visual prototype</h2><p>This corrects the dominant representation gaps; it does not claim to match the concept's final photorealism. Bubble interfaces are raster approximations. Thickness is an authored chord approximation; PNO does not lens the base mesh curvature. The separate F0-derived native refraction experiment passes seven focused optical contract tests, but failed rendered acceptance through self-refraction. Enabling standard separated translucency did not resolve it. It is not the default hero. No traced multiple interfaces or caustics are claimed. This quick hero pass has actual shader/resource and image checks, not the prior 82-capture campaign proof or a performance benchmark.</p>
<p><a href="Amber-Original-IllustrativeConcept.png">Full illustrative concept sheet</a> · <a href="AmberHero-ReviewReceipt.json">Source/capture receipt</a> · <a href="Amber-Inclusions-Gallery.html">Previous prototype gallery</a></p></main></html>'''
    page = OUTPUT / 'Amber-Fidelity-Review.html'
    page.write_text(content, encoding='utf-8')
    source_files = [ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/AmberHeroLeaf.ush', ROOT / 'Tools/UsfMaterials/amber_hero_scene.py', ROOT / 'Tools/UsfMaterials/prepare_amber_hero.py']
    receipt = dict(status='visual_prototype_ready_for_review', astra_consulted=True,
        captures={name: hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest() for name in [old, new, reference.name]},
        sources={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
        page_sha256=hashlib.sha256(page.read_bytes()).hexdigest(),
        license='https://www.cgbookcase.com/textures', leaf='https://www.cgbookcase.com/textures/autumn-leaf-31',
        limits=['Not full concept fidelity', 'Approximate bubble interfaces and chord thickness', 'PNO lacks base-curvature lensing', 'Browser layout not verified'])
    (OUTPUT / 'AmberHero-ReviewReceipt.json').write_text(json.dumps(receipt, indent=2))
    print(page)


if __name__ == '__main__':
    main()
