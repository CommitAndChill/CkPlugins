"""Review actual native BSDF captures, controls and reload evidence."""
import html
import json
from pathlib import Path
from advanced_bsdf_settings import LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Saved/UsfMaterialGallery'
PREFIX = 'AdvancedBsdf'
TITLES = {'NativeRubyVelvet': 'Ruby velour', 'NativeVarnishedWalnut': 'Varnished walnut',
          'NativeResinCarbon': 'Resin carbon weave', 'NativeCopper': 'Clean copper'}
DESCRIPTIONS = {
    'NativeRubyVelvet': 'Photographed nap and a colored native fuzz response. Fuzz weight and tint are independent of the textured body; the on/off difference is subtle in the studio pose.',
    'NativeVarnishedWalnut': 'Long walnut grain with a native simplified varnish coat. Base and coat roughness have separate controls.',
    'NativeResinCarbon': 'Crossed-tow texture with a smooth native resin finish over a rougher dielectric body.',
    'NativeCopper': 'Colored conductor reflectance with texture-backed finish variation and almost no diffuse response.'}


def picture(name, label, caption):
    file = f'{PREFIX}-{name}-{label}.png'
    if not (OUT/file).is_file():
        raise RuntimeError('Missing actual capture: '+file)
    return f'<figure><a href="{file}"><img src="{file}" alt="{html.escape(caption)}" loading="lazy"></a><figcaption>{html.escape(caption)}</figcaption></figure>'


def main():
    proof = json.loads((OUT/f'{PREFIX}-RenderedProof.json').read_text())
    preparation = json.loads((OUT/'AdvancedBsdfPreparation.json').read_text())
    if not proof['passed'] or not proof['restored'] or set(preparation['looks']) != set(LOOKS):
        raise RuntimeError('Successful complete preparation and restored rendered proof required')
    cards = []
    for name, recipe in LOOKS.items():
        record = preparation['looks'][name]
        controls = ''
        if recipe['slab_fuzz']:
            controls = picture(name, 'FuzzOff', 'Same material, fuzz weight zero')
        if recipe['surface_graph'] == 3:
            controls = picture(name, 'CoatOff', 'Same material, coat coverage zero') + picture(name, 'CoatRough', 'Same material, coat roughness 0.65')
        frames = len(proof['orbits'][name]['frames'])
        seconds = frames/proof['orbits'][name]['fps']
        source = html.escape(record['source_url'], quote=True)
        shader = (ROOT/f'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/{name}.ush').as_uri()
        cards.append(f'''<article><h2>{TITLES[name]}</h2><p>{DESCRIPTIONS[name]}</p>
{picture(name, 'Close', 'Studio / final material')}<div class="views">{picture(name, 'Macro', 'Surface detail')}{picture(name, 'Gameplay', 'At a distance')}</div>
<video controls loop muted playsinline preload="metadata" src="{PREFIX}-{name}-Orbit.mp4"></video>
<p class="caption">{frames} actual captured light phases · {seconds:g} seconds at 4 fps · not a real-time performance recording</p>
<details><summary>Compare native response controls</summary><div class="views">{controls or '<p>Conductor F0, normal strength, roughness and color variation are live .ush inputs.</p>'}</div></details>
<details><summary>Inspect live source edit and recovery</summary><div class="views">{picture(name, 'Edited', 'Temporary .ush edit, same master and MID')}{picture(name, 'Restored', 'Exact source restored, same master and MID')}</div></details>
<p class="links"><a href="{source}">CC0 texture source</a><a href="{shader}">Edit .ush</a></p></article>''')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CkUsf / Advanced native BSDF studies</title><style>
body{margin:0;background:#141920;color:#ecf0f6;font:16px/1.55 system-ui}header,main,footer{max-width:1440px;margin:auto;padding:32px}header{padding-bottom:0}h1{font-size:38px;line-height:1.15;margin:8px 0}h2{margin-top:0}p{max-width:1000px}.eyebrow,.caption{color:#acbacb;font-size:14px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:28px}article{background:#202833;padding:22px;border:1px solid #344253;border-radius:12px}figure{margin:0 0 15px}img,video{display:block;width:100%;border-radius:6px}figcaption{color:#acbacb;font-size:13px;margin:5px 0}.views{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}a{color:#a4d0ff}summary{cursor:pointer;padding:12px 0}details{border-top:1px solid #344253}.links a,footer a{margin-right:20px}footer{padding-top:0}.badge{display:inline-block;padding:4px 10px;border:1px solid #486b57;border-radius:5px;color:#b5dfc5}</style>
<header><p class="eyebrow">CKUSF / NATIVE BSDF SURFACE STUDIES</p><h1>Four surfaces. Distinct light response.</h1>
<p>Texture-backed materials authored in .ush, feeding Unreal Engine 5.8 native BSDF nodes directly. Same logo-free shader ball, studio rig and exposure. Clean, intact finishes.</p>
<p class="badge">Rendered source reload + recovery verified on existing material instances</p></header>
<main class="grid">''' + ''.join(cards) + '''</main>
<footer><p>Sampling, UV scale/rotation, normal strength, roughness, color and specialized fuzz/coat inputs remain live-editable through .ush. Studio captures use temporary TAA / 100% resolution; all overrides, lights and renderer settings were restored.</p>
<p>Renderer scope: Blendable GBuffer. Fuzz roughness is fixed by this renderer. Native Simple Clear Coat has fixed top F0=0.04 and one shared normal with the current settings; this is a supported simplified coat, not unrestricted multilayer transport. The carbon weave backing is authored texture data, not a carbon photogrammetry scan. Copper has no patina.</p>
<p>Original source maps are retained. Velvet and walnut use separately recorded encoded-RGB 8-bit derivatives, with no gamma conversion or grading; velvet retains the existing documented runtime resize policy.</p>
<p><a href="AdvancedBsdfPreparation.json">Texture provenance and bindings</a><a href="AdvancedBsdfRefinement.json">Final presentation defaults</a><a href="AdvancedBsdf-RenderedProof.json">Render, controls and restoration evidence</a><a href="Native-BSDF-Gallery.html">Earlier Slab and Toon pair</a></p></footer></html>'''
    (OUT/'Advanced-BSDF-Gallery.html').write_text(page, encoding='utf-8')


if __name__ == '__main__':
    main()
