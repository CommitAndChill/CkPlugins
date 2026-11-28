"""Present the separately owned environmental POM/WPO inspection collection."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'


def main():
    manifest = json.loads((ROOT / 'Plugins/CkTests/Resources/CkUsf/Environment2Textures/Manifest.json').read_text(encoding='utf-8'))
    proof = json.loads((OUTPUT / 'Environment1-Proof.json').read_text(encoding='utf-8'))
    if proof.get('passed') is not True or proof.get('restored') is not True:
        raise RuntimeError('Environment proof must pass and restore before gallery publication')
    record = manifest['materials']['gravel']
    bindings = {}
    for channel in ['BaseColor', 'Normal', 'Roughness', 'Height', 'AO']:
        runtime = 'T_EnvironmentGravelV2_' + channel
        if record['maps'][channel]['runtime_name'] != runtime:
            raise RuntimeError('Environment gallery requires the selected V2 texture family')
        bindings[channel + 'Map'] = '/CkFoundation/CkUsf/Textures/Environment/' + runtime + '.' + runtime
    for capture in proof['captures'].values():
        if any(station['textures'] != bindings for station in capture['state']['environment'].values()):
            raise RuntimeError('Environment gallery captures do not use the selected V2 source')
    source = record.get('asset_url', record.get('source_url', ''))
    attribution = '<a href="' + html.escape(source, quote=True) + '">Recorded gravel source</a>' if source else 'See source manifest.'
    cards = []
    for label, capture in proof['captures'].items():
        image = Path(capture['image'])
        if image.name != str(image) or image.suffix.lower() != '.png' or not (OUTPUT / image).is_file():
            raise RuntimeError('Invalid or missing captured environment image')
        title = html.escape(label)
        filename = html.escape(image.name, quote=True)
        cards.append(f'<article><h2>{title}</h2><a href="{filename}"><img src="{filename}" alt="{title} saved Unreal capture"></a></article>')
    page = '''<!doctype html><meta charset="utf-8"><title>CkUsf environment collection / gravel</title>
<style>body{font:16px system-ui;background:#171b22;color:#e7edf6;margin:32px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:20px}article{background:#222a35;padding:16px}img{width:100%}a{color:#9dcbff}h2{font-size:19px}</style>
<h1>Gravel ground / POM and vertex displacement</h1>
<p>Selected source: the versioned Environment2 gravel texture set. The earlier soil source and its initial evidence remain a separate candidate.</p>
<p>This separate two-station collection uses the same recorded BC/N/R/Height maps, with source AO when available. POM changes apparent texture coordinates on a flat surface; it does not change raster depth, silhouette or native shadows. The dense-grid WPO station moves real vertices and compares independently encoded raster depth. CPU collision remains unchanged. The neutral slab sits below the maximum recess, and the patch perimeter remains open.</p>
<p>Native and temporary TAA captures are individually labeled. Geometric-normal inspection disables the sourced detail normal. Sampled still frames do not establish motion quality, temporal stability, shadow correctness or performance. Same-object source edits and restoration are recorded separately from user artistic acceptance.</p>
<p><a href="Environment1-Proof.json">Control, source and restoration proof</a> Â· <a href="Environment1Preparation.json">Import, precision and grid receipt</a> Â· <a href="Environment1-Verification.json">Independent reconciliation</a> Â· <a href="Environment1-Sources.json">Exact source manifest</a></p>'''
    page += '<p>' + attribution + '</p><p>' + html.escape(record.get('identity_notes', 'See the recorded source manifest.')) + '</p>'
    (OUTPUT / 'Environment1-Gallery.html').write_text(page + '<main>' + '\n'.join(cards) + '</main>', encoding='utf-8')
    (OUTPUT / 'Environment1-Sources.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(OUTPUT / 'Environment1-Gallery.html')


if __name__ == '__main__':
    main()
