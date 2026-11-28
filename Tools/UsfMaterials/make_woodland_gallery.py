"""Publish recorded woodland evidence locally; no renderer or studio calls."""
import hashlib
import html
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
MANIFEST = ROOT / 'Plugins/CkTests/Resources/CkUsf/WoodlandPatchV3/Manifest.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(path):
    return html.escape(Path(os.path.relpath(path, OUTPUT)).as_posix(), quote=True)


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    preparation = json.loads((OUTPUT/'WoodlandPreparation.json').read_text(encoding='utf-8'))
    proof = json.loads((OUTPUT/'Woodland-Proof.json').read_text(encoding='utf-8'))
    verification = json.loads((OUTPUT/'Woodland-Verification.json').read_text(encoding='utf-8'))
    if (proof.get('passed') is not True or proof.get('restored') is not True or verification.get('passed') is not True
            or preparation['selected_source'] != 'WoodlandPatchV3'
            or proof['manifest_sha256'] != preparation['manifest_sha256'] or preparation['manifest_sha256'] != digest(MANIFEST)
            or verification['proof_sha256'] != digest(OUTPUT/'Woodland-Proof.json')
            or verification['preparation_sha256'] != digest(OUTPUT/'WoodlandPreparation.json')
            or verification['manifest_sha256'] != digest(MANIFEST)):
        raise RuntimeError('Selected V3 preparation, restored proof and independent verification must agree before publication')
    shader = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/EnvironmentWoodland.ush'
    if verification['source_shader_sha256'] != digest(shader):
        raise RuntimeError('Woodland shader changed after verification')
    bindings = {channel+'Map': '/CkFoundation/CkUsf/Textures/Environment/'+info['runtime_name']+'.'+info['runtime_name']
                for channel, info in manifest['maps'].items()}
    for capture in proof['captures'].values():
        path = OUTPUT / capture['image']
        if (path.parent.resolve() != OUTPUT.resolve() or path.suffix.lower() != '.png'
                or digest(path) != capture['sha256'] or verification['capture_sha256'].get(path.name) != digest(path)
                or any(station['textures'] != bindings for station in capture['state']['environment'].values())):
            raise RuntimeError('Gallery capture is stale or does not bind the selected source')

    # Identical center crops and resize only; preserve original exposure, color and contrast.
    width, height, bar = 480, 330, 28
    sheet = Image.new('RGB', (width*2, (height+bar)*3), '#171b22')
    draw = ImageDraw.Draw(sheet)
    cards = []
    for row, view in enumerate(['Oblique', 'Low', 'Top']):
        for column, station in enumerate(['pom', 'displacement']):
            title = ('POM / flat raster' if station == 'pom' else 'WPO / real vertices')+' / '+view
            name = f'Woodland-TAA-{station}-{view}.png'
            native = f'Woodland-Native-{station}-{view}.png'
            with Image.open(OUTPUT/name) as source:
                crop = ImageOps.fit(source.convert('RGB'), (width, height), method=Image.Resampling.LANCZOS, centering=(.5, .5))
            sheet.paste(crop, (column*width, row*(height+bar)+bar))
            draw.text((column*width+10, row*(height+bar)+8), title, fill='#e7edf6')
            cards.append(f'<article><h2>{html.escape(title)}</h2><a href="{name}"><img src="{name}" alt="Actual Unreal TAA {html.escape(title)}"></a>'
                         f'<p><a href="{name}">TAA original</a> &middot; <a href="{native}">Native AA0 original</a></p></article>')

    sources = manifest['sources']
    leaves = sources['leaves']['receipt']
    soil, stone = sources['soil']['material'], sources['stones']['material']
    attributions = []
    for label, url in [('ambientCG '+leaves['asset']+' photo leaf atlas (CC0)', leaves['source_url']),
                       ('Poly Haven gravelly_sand soil (CC0)', soil['source_url']),
                       ('ambientCG Granite002A stones (CC0)', stone['source_url'])]:
        attributions.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
    beauty = MANIFEST.parent / manifest['beauty']['path']
    blend = MANIFEST.parent / manifest['blend']['path']
    if digest(beauty) != manifest['beauty']['sha256'] or digest(blend) != manifest['blend']['sha256']:
        raise RuntimeError('Selected Blender source changed')
    maps = []
    for channel, info in manifest['maps'].items():
        path = (MANIFEST.parent/info['path']).resolve()
        if not path.is_relative_to(MANIFEST.parent.resolve()) or digest(path) != info['sha256']:
            raise RuntimeError('Selected map path/hash differs')
        maps.append(f'<article><h2>{html.escape(channel)} / {info["bit_depth"]}-bit {html.escape(info["color_space"])}</h2>'
                    f'<a href="{link(path)}"><img src="{link(path)}" alt="Actual selected {html.escape(channel)} source map"></a></article>')
    span = manifest['height']['range_cm']
    controls = {key: value['values'] for key, value in proof['initial_state']['environment'].items()}
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CkUsf woodland / POM and displacement</title><style>
body{font:16px/1.5 system-ui;background:#171b22;color:#e7edf6;margin:0 auto;padding:28px;max-width:1240px}
h1{font-size:30px}h2{font-size:18px;margin:0 0 12px}a{color:#9dcbff}p{max-width:1100px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.maps{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
article,details{background:#222a35;padding:16px;border-radius:8px;margin-bottom:16px}img{display:block;width:100%;height:auto}
pre{overflow:auto;white-space:pre-wrap;font-size:12px}.source{max-width:650px}small{color:#b5c3d6}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<h1>Woodland patch / POM and vertex displacement</h1>
<p>Actual Unreal captures of the selected texture-backed, authored woodland heightfield. Left: POM on a flat grid. Right: vertex displacement on a 256 &times; 256-cell grid. TAA beauty views below use temporary AA2 at 100%; linked native counterparts use AA0 at 87%.</p>
'''
    page += f'<p>Physical footprint: 80 &times; 80 cm. Geometry-derived normalized 16-bit height spans {span:.6f} cm; both stations use that calibrated relief and HeightMip 0. The full aligned baked normal supplies surface forms once.</p>'
    page += '<p>POM changes sampled UV appearance without raster silhouette/depth displacement. WPO moves real vertices; CPU collision remains unchanged. A neutral slab sits below the maximum recess. This topmost-surface heightfield cannot reproduce leaf undersides, overhangs or hidden layers. Clamp sampling preserves a non-tileable patch. Stills do not establish shadow correctness, motion quality, temporal stability or GPU cost.</p>'
    page += '<p><a href="Woodland-ContactSheet.png">Side-by-side contact sheet</a> (identical center crops and resize; no grading). '
    page += '<a href="Woodland-Proof.json">Controls and source reload proof</a> &middot; <a href="Woodland-Verification.json">Independent evidence reconciliation</a> &middot; <a href="WoodlandPreparation.json">Import and grid receipt</a> &middot; '
    page += f'<a href="{link(MANIFEST)}">Selected source manifest</a> &middot; <a href="{link(shader)}">USH source</a> &middot; <a href="{link(blend)}">Packed editable Blender source</a></p>'
    page += '<div class="grid">'+''.join(cards)+'</div>'
    page += '<h2>Source authoring preview / Blender, separate from Unreal</h2>'
    page += f'<article class="source"><a href="{link(beauty)}"><img src="{link(beauty)}" alt="Native Blender lit source preview, not an Unreal render"></a><p>Blender source beauty. Lighting and framing differ from the Unreal captures.</p></article>'
    page += '<p>'+ ' &middot; '.join(attributions)+'</p><p>'+html.escape(manifest['source'])+' '+html.escape(manifest['composition'])+'</p>'
    page += '<p>Leaf species and physical photo-atlas displacement amplitude are unverified; folds, placement and strength are authored. Source authoring previews and rendered controls are distinct from user artistic acceptance.</p>'
    page += '<h2>Actual aligned source maps</h2><div class="grid maps">'+''.join(maps)+'</div>'
    for title, values in [('Exact baseline controls', controls), ('Recomputed control, noise and recovery metrics', verification['recomputed_metrics']),
                          ('Generated material statistics / instruction and sampler counts, not GPU timings', preparation['statistics'])]:
        page += '<details><summary>'+html.escape(title)+'</summary><pre>'+html.escape(json.dumps(values, indent=2))+'</pre></details>'
    page += '<small>Selected WoodlandPatchV3. Earlier rejected source drafts remain separate. Image and source hashes are recorded in the linked receipts.</small></html>'
    # All prerequisites are checked before either publication output is written.
    sheet.save(OUTPUT/'Woodland-ContactSheet.png')
    (OUTPUT/'Woodland-Gallery.html').write_text(page, encoding='utf-8')
    print(OUTPUT/'Woodland-Gallery.html')


if __name__ == '__main__':
    main()
