"""Build a review page only from completed real Adaptive captures and restoration proof."""
import html
import hashlib
import json
from pathlib import Path
import subprocess
from adaptive_bsdf_settings import LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/UsfMaterialGallery'


def main():
    proof = json.loads((OUT/'AdaptiveBsdf-RenderedProof.json').read_text(encoding='utf-8'))
    if not proof['passed'] or not proof['restored']:
        raise RuntimeError('Successful rendered and restored proof is required')
    for capture in proof['captures'].values():
        filename = capture['file']
        if Path(filename).name != filename or hashlib.sha256((OUT/filename).read_bytes()).hexdigest() != capture['sha256']:
            raise RuntimeError('Capture no longer matches rendered proof: ' + filename)
    canonical = json.loads((OUT/'AdaptiveBsdf-CanonicalCaptureReceipt.json').read_text(encoding='utf-8'))
    if not canonical['passed'] or canonical['proof_sha256'] != hashlib.sha256((OUT/'AdaptiveBsdf-RenderedProof.json').read_bytes()).hexdigest():
        raise RuntimeError('Canonical captures no longer match rendered proof')
    if set(canonical['captures']) != set(proof['captures']):
        raise RuntimeError('Canonical capture roster differs')
    for key, capture in canonical['captures'].items():
        if (not capture['decoded_pixels_identical'] or capture['raw_sha256'] != proof['captures'][key]['sha256'] or
                hashlib.sha256((OUT/capture['display_file']).read_bytes()).hexdigest() != capture['display_sha256']):
            raise RuntimeError('Canonical pixels or capture hash differ: ' + key)
    def picture(name, label, caption):
        filename = canonical['captures'][name + '-' + label]['display_file']
        if not (OUT/filename).is_file():
            raise RuntimeError('Missing actual capture: ' + filename)
        return f'<figure><a href="{filename}"><img src="{filename}" loading="lazy" alt="{html.escape(caption)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>'
    cards = []
    for name, recipe in LOOKS.items():
        frames = [proof['captures'][name + '-Orbit%02d' % index]['sha256'] for index in range(24)]
        sequence_hash = hashlib.sha256(''.join(frames).encode('ascii')).hexdigest()[:12]
        video = 'AdaptiveBsdf-' + name + '-Orbit-' + sequence_hash + '.mp4'
        if not (OUT/video).exists():
            subprocess.run(['ffmpeg', '-v', 'error', '-n', '-framerate', '8', '-i',
                str(OUT/'AdaptiveCanonical'/('AdaptiveBsdf-' + name + '-Orbit%02d.png')), '-frames:v', '24',
                '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(OUT/video)], check=True)
        title = 'Candy metal / absorbing coat' if name == 'AdaptiveCandyPaint' else 'Slubbed silk / two directional lobes'
        description = ('Two retained slabs: a smooth dyed upper medium filters a textured metallic base. Thickness changes absorption; the outer reflection has its own roughness and normal.'
                       if name == 'AdaptiveCandyPaint' else
                       'Licensed crepe-satin detail plus authored yarn thickenings. Two retained anisotropic BSDF responses have independent axes, roughness and weighting. The yarn detail is subtle on the full ball; use the macro and isolated-lobe comparisons. UV scale deliberately enlarges the backing about 2.9 times for inspection.')
        controls = [('ThinDye', 'Thinner dyed medium'), ('CoatRough', 'Rougher upper surface')] if name == 'AdaptiveCandyPaint' else [('LobeAOnly', 'First lobe only'), ('LobeBOnly', 'Second lobe only')]
        compiled = proof['initial']['looks'][name]['compiled']
        shader = (ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'/f'{name}.ush').as_uri()
        cards.append(f'''<article><h2>{title}</h2><p>{description}</p>
<p class="badge">{compiled['closure_count']} compiled BSDF closures Â· {compiled['uint_per_pixel']*4} bytes material payload</p>
{picture(name,'Close','Material under studio lighting')}
<video controls loop muted playsinline preload="metadata" src="{video}"></video>
<p class="caption">24 captured inspection-light phases Â· 3-second playback Â· not a GPU performance recording</p>
<div class="views">{picture(name,'Macro','Close surface detail')}{picture(name,'Gameplay','At a distance')}</div>
<details><summary>Compare individual responses</summary><div class="views">{''.join(picture(name,label,caption) for label,caption in controls)}</div></details>
<details><summary>Live .ush edit and exact recovery</summary><div class="views">{picture(name,'SourceEdited','Temporary numeric source edit, same master and MID')}{picture(name,'SourceRecovered','Original source restored')}{picture(name,'HelperEdited','Shared helper edit')}{picture(name,'HelperRecovered','Shared helper restored')}</div></details>
<p><a href="{shader}">Open .ush source</a></p><p class="caption">{html.escape(recipe['identity_notes'])}</p></article>''')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CkUsf / Retained Substrate layers</title><style>
body{margin:0;background:#10161f;color:#e8edf5;font:16px/1.55 system-ui}header,main,footer{max-width:1440px;margin:auto;padding:30px}h1{font-size:40px;line-height:1.15}h2{font-size:25px}p{max-width:1000px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:28px}article{padding:22px;background:#1c2634;border:1px solid #374558;border-radius:12px}figure{margin:0 0 14px}img,video{width:100%;display:block;border-radius:6px}.caption,figcaption{color:#b3c1d3;font-size:13px}.views{display:grid;grid-template-columns:1fr 1fr;gap:12px}a{color:#9bceff}summary{cursor:pointer;padding:14px 0}details{border-top:1px solid #374558}.badge{color:#b5e5c6;font-size:14px}footer a{margin-right:18px}</style>
<header><p class="caption">CKUSF / ADAPTIVE SUBSTRATE STUDIES</p><h1>Separate layers. Distinct responses to light.</h1>
<p>Two texture-backed material studies using Unreal Engine's native Substrate slabs and operators. Sampling and numerical surface properties remain live-editable through .ush. The approved logo-free shader ball is preserved.</p>
<p>Dedicated offscreen Adaptive profile; the normal Blendable gym keeps its existing renderer configuration.</p></header><main class="grid">''' + ''.join(cards) + '''</main>
<footer><p>Inspired by <a href="https://www.unrealengine.com/news/get-over-280-production-ready-automotive-substrate-materials-for-ue-5-7-free-on-fab">Epic's automotive finishes</a> and <a href="https://blog.adobe.com/en/publish/2025/04/03/bringing-zorah-to-life-how-substance-3d-tools-powered-nvidias-ambitious-tech-demo">Zorah's multi-lobe silk</a>. Independent recreations; original reference graphs and textures were not supplied or copied.</p>
<p>The first paint study has two slabs, with no third clearcoat or native flake/glint population. Silk uses authored slub detail over satin backing. NVIDIA neural acceleration is not used. Compiled payload counts are material data, not complete framebuffer allocation or timing measurements.</p>
<p><a href="AdaptiveBsdfPreparation.json">Texture bindings and provenance</a><a href="AdaptiveBsdf-RenderedProof.json">Controls, live edits and restoration evidence</a><a href="AdaptiveBsdf-CanonicalCaptureReceipt.json">Display image provenance</a><a href="Advanced-BSDF-Gallery.html">Earlier Blendable studies</a></p></footer></html>'''
    (OUT/'Adaptive-BSDF-Gallery.html').write_text(page, encoding='utf-8')
    print(str(OUT/'Adaptive-BSDF-Gallery.html'))


if __name__ == '__main__':
    main()
