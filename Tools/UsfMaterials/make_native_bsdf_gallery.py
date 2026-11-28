"""Build the native BSDF review page from successful actual-renderer proof."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'


def main():
    prefix = 'NativeBsdf-ThreeLevel'
    proof = json.loads((OUTPUT / (prefix+'-RenderedProof.json')).read_text())
    if not proof['passed'] or not proof['restored']:
        raise RuntimeError('A successful restored rendered proof is required')
    cards = []
    for name, title, description in [
        ('NativePorcelainSlab', 'Native Slab · ceramic', 'A dielectric Slab with separate tile and grout response.'),
        ('NativeCeramicToon', 'Native Toon · ceramic', 'The engine Toon BSDF with a saved three-level native diffuse ramp; factory specular and GI settings retained.')]:
        views = ''.join(f'<a href="{prefix}-{name}-{view}.png">{view}</a> ' for view in ['Close', 'Macro', 'Gameplay', 'Edited', 'Restored'])
        cards.append(f'<article><h2>{title}</h2><p>{description}</p>'
                     f'<img src="{prefix}-{name}-Close.png" alt="{title}">'
                     f'<p>{views}</p><video controls loop muted preload="metadata" src="{prefix}-{name}-Orbit.mp4"></video>'
                     '<p>Inspection Point light: 24 captured phases, 4 fps. This preview shows lighting response; it is not real-time performance footage.</p></article>')
    page = '''<!doctype html><meta charset="utf-8"><title>CkUsf native BSDF examples</title>
<style>body{font:16px system-ui;background:#171b22;color:#e7edf6;margin:32px;line-height:1.5}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#222a35;padding:20px;border-radius:12px}img,video{width:100%}a{color:#9dcbff;margin-right:10px}h1,h2{line-height:1.2}</style>
<h1>CkUsf / native Slab and Toon</h1>
<p>Actual Unreal Engine 5.8 renders on the approved logo-free shader ball. Both examples use the same CC0 base-color, normal, roughness and aligned tile-mask textures. Matched studio captures use temporary TAA and 100% screen percentage; the original renderer and light settings were restored.</p>
<p>Each .ush source controls texture sampling, UV scale/rotation, normals, roughness, color and numeric BSDF inputs. The Toon ramp is native profile asset data. Native BSDF nodes feed FrontMaterial directly; no post-process lighting extraction or replacement light model is used.</p>
<main>''' + ''.join(cards) + '''</main>
<p>Scope: opaque SurfaceLit, one BSDF per example, Blendable GBuffer. This is a first matched pair, not a full multilayer BSDF catalog. The ceramic source does not establish porcelain composition.</p>
<p><a href="https://ambientcg.com/a/Tiles133A">CC0 texture source</a><a href="NativeBsdfPreparation.json">Texture bindings and provenance</a><a href="NativeBsdf-ThreeLevel-RenderedProof.json">Same-instance source edit and restoration evidence</a><a href="NativeBsdf-RenderedProof.json">Factory-profile baseline proof</a><a href="NativeToonProfile.json">Native ramp recipe</a></p>'''
    (OUTPUT / 'Native-BSDF-Gallery.html').write_text(page, encoding='utf-8')


if __name__ == '__main__':
    main()
