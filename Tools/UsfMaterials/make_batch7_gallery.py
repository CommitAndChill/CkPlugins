"""Present original batch-seven Unreal captures and recorded material identities without grading."""
from pathlib import Path
import html
import json
from PIL import Image, ImageDraw, ImageFont
from capture_batch7 import LOOKS


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
LABELS = ['Nylon-style textile', 'Slate', 'Clean copper', 'Glossy molded plastic', 'Wax-style surface', 'Photo-derived fiberglass weave']



def main():
    manifest = json.loads((ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch7Textures/Manifest-v2.json').read_text(encoding='utf-8'))
    captures = json.loads((OUTPUT / 'Batch7-LitCaptures.json').read_text(encoding='utf-8'))
    for name in LOOKS:
        record = next(value for value in manifest['materials'].values() if value['look_id'] == name)
        family = 'LibraryFiberglassV2' if name == 'LibraryFiberglass' else name
        bindings = {}
        for channel in ['BaseColor', 'Normal', 'Roughness']:
            runtime = 'T_' + family + '_' + channel
            if record['maps'][channel]['runtime_name'] != runtime:
                raise RuntimeError('Gallery source runtime family differs: ' + name)
            bindings[channel + 'Map'] = '/CkFoundation/CkUsf/Textures/Library/' + runtime + '.' + runtime
        for prefix in ['Batch7', 'Batch7-Preview']:
            for view in ['Close', 'Macro', 'Gameplay']:
                if captures[prefix + '-' + name][view]['state']['library'][name]['textures'] != bindings:
                    raise RuntimeError('Saved gallery capture does not use the selected source: ' + name + '/' + view)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 19)
    sheet = Image.new('RGB', (1440, 1170), '#171b22')
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 12), 'CkUsf mixed material library / batch 7', fill='white', font=font)
    draw.text((20, 45), 'Saved Unreal captures / cropped contact sheet / original files linked', fill='#b8c4d6', font=font)
    cards = []
    for index, (name, label) in enumerate(zip(LOOKS, LABELS)):
        filename = f'Batch7-Preview-{name}-Close.png'
        image = Image.open(OUTPUT / filename).convert('RGB')
        width, height = image.size
        crop = image.crop((int(width * .18), int(height * .08), int(width * .81), int(height * .98)))
        crop.thumbnail((464, 505), Image.Resampling.LANCZOS)
        x, y = (index % 3) * 480, 85 + (index // 3) * 540
        sheet.paste(crop, (x + (480 - crop.width) // 2, y + 28))
        draw.text((x + 12, y), label, fill='white', font=font)
        links = ' '.join(f'<a href="Batch7-Preview-{name}-{view}.png">{view}</a>' for view in ['Close', 'Macro', 'Gameplay'])
        baseline = ' '.join(f'<a href="Batch7-{name}-{view}.png">{view} native AA</a>' for view in ['Close', 'Macro', 'Gameplay'])
        record = next(value for value in manifest['materials'].values() if value['look_id'] == name)
        source = record.get('asset_url', record.get('source_url', ''))
        attribution = f'<a href="{html.escape(source, quote=True)}">Recorded source</a>' if source else '<a href="Batch7-Sources.json">Source manifest</a>'
        provenance = html.escape(record.get('identity_notes', 'See the source manifest for material identity, license and modifications.'))
        if name == 'LibraryFiberglass':
            provenance += ' Selected v2 uses the fine weave photograph of actual fiberglass; normal and roughness maps are authored estimates derived from that photograph, rather than measured scans.'
        cards.append(f'<article><h2>{label}</h2><a href="{filename}"><img src="{filename}" alt="{label} saved Unreal render"></a><p>{links}</p><p>{baseline}</p>{attribution}<p>{provenance}</p></article>')
    page = '''<!doctype html><meta charset="utf-8"><title>CkUsf library / batch 7</title>
<style>body{font:16px system-ui;background:#171b22;color:#e7edf6;margin:32px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#222a35;padding:16px;border-radius:12px}img{width:100%}a{color:#9dcbff;margin-right:10px}h2{font-size:22px}</style>
<h1>CkUsf mixed material library / batch 7</h1><p>Saved Unreal game-viewport captures. The contact sheet is cropped and resized for layout; original captures are linked. Preview/native filenames distinguish capture passes. Their actual settings and final restoration are checked by the evidence reconciliation.</p>
<p>Every material stays authored through .ush with recorded base-color, normal and roughness maps. Material identity, finish interpretation and any source substitution follow the exact manifest; labels do not certify polymer, wax or fiber composition. Copper uses authored conductor reflectance. The wax surface response does not establish measured thickness-dependent scattering. Source modifications and retained limits remain recorded separately from user artistic acceptance.</p>
<p><a href="Batch1-Gallery.html">Batch 1</a><a href="Batch2-Gallery.html">Batch 2</a><a href="Batch3-Gallery.html">Batch 3</a><a href="Batch4-Gallery.html">Batch 4</a><a href="Batch5-Gallery.html">Batch 5</a><a href="Batch6-Gallery.html">Batch 6</a><a href="Batch7-Sources.json">Exact source manifest</a><a href="Batch7-LitCaptures.json">Capture records</a><a href="Batch7-LiveReloadProof.json">Live source proof</a><a href="Batch7-ControlProof.json">Controls and restoration</a><a href="Batch7-Costs.json">Material statistics</a><a href="Batch7-Gate.exit.json">Focused generation gate</a><a href="Batch7-Verification.json">Independent reconciliation</a></p><main>'''
    (OUTPUT / 'Batch7-Gallery.html').write_text(page + '\n'.join(cards) + '</main>', encoding='utf-8')
    (OUTPUT / 'Batch7-Sources.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    sheet.save(OUTPUT / 'Batch7-ContactSheet-TAA.png')
    print(OUTPUT / 'Batch7-Gallery.html')


if __name__ == '__main__':
    main()
