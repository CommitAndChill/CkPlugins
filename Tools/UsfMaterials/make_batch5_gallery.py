"""Present original batch-five Unreal captures and recorded material identities without grading."""
from pathlib import Path
import html
import json
from PIL import Image, ImageDraw, ImageFont
from capture_batch5 import LOOKS


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
LABELS = ['Denim', 'Concrete', 'Brick', 'Stainless-style metal finish', 'Plywood edge', 'Cardboard']



def main():
    manifest = json.loads((ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch5Textures/Manifest.json').read_text(encoding='utf-8'))
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 19)
    sheet = Image.new('RGB', (1440, 1170), '#171b22')
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 12), 'CkUsf mixed material library / batch 5', fill='white', font=font)
    draw.text((20, 45), 'Saved Unreal captures / cropped contact sheet / original files linked', fill='#b8c4d6', font=font)
    cards = []
    for index, (name, label) in enumerate(zip(LOOKS, LABELS)):
        filename = f'Batch5-Preview-{name}-Close.png'
        image = Image.open(OUTPUT / filename).convert('RGB')
        width, height = image.size
        crop = image.crop((int(width * .18), int(height * .08), int(width * .81), int(height * .98)))
        crop.thumbnail((464, 505), Image.Resampling.LANCZOS)
        x, y = (index % 3) * 480, 85 + (index // 3) * 540
        sheet.paste(crop, (x + (480 - crop.width) // 2, y + 28))
        draw.text((x + 12, y), label, fill='white', font=font)
        links = ' '.join(f'<a href="Batch5-Preview-{name}-{view}.png">{view}</a>' for view in ['Close', 'Macro', 'Gameplay'])
        baseline = ' '.join(f'<a href="Batch5-{name}-{view}.png">{view} native AA</a>' for view in ['Close', 'Macro', 'Gameplay'])
        record = next(value for value in manifest['materials'].values() if value['look_id'] == name)
        source = record.get('asset_url', record.get('source_url', ''))
        attribution = f'<a href="{html.escape(source, quote=True)}">Recorded source</a>' if source else '<a href="Batch5-Sources.json">Source manifest</a>'
        provenance = html.escape(record.get('identity_notes', 'See the source manifest for material identity, license and modifications.'))
        cards.append(f'<article><h2>{label}</h2><a href="{filename}"><img src="{filename}" alt="{label} saved Unreal render"></a><p>{links}</p><p>{baseline}</p>{attribution}<p>{provenance}</p></article>')
    page = '''<!doctype html><meta charset="utf-8"><title>CkUsf library / batch 5</title>
<style>body{font:16px system-ui;background:#171b22;color:#e7edf6;margin:32px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#222a35;padding:16px;border-radius:12px}img{width:100%}a{color:#9dcbff;margin-right:10px}h2{font-size:22px}</style>
<h1>CkUsf mixed material library / batch 5</h1><p>Saved Unreal game-viewport captures. The contact sheet is cropped and resized for layout; original captures are linked. Preview/native filenames distinguish capture passes. Their actual settings and final restoration are checked by the evidence reconciliation.</p>
<p>Every material stays authored through .ush. The six surfaces use their recorded base-color, normal and roughness maps with independent material controls. The stainless-style finish uses authored neutral metal reflectance; its source does not establish alloy composition. Plywood shows the sourced layered edge, rather than a veneer face. Rendered evidence does not establish measured optical properties; source identity and modifications remain recorded in the manifest.</p>
<p><a href="Batch1-Gallery.html">Batch 1</a><a href="Batch2-Gallery.html">Batch 2</a><a href="Batch3-Gallery.html">Batch 3</a><a href="Batch4-Gallery.html">Batch 4</a><a href="Batch5-Sources.json">Exact source manifest</a><a href="Batch5-LitCaptures.json">Capture records</a><a href="Batch5-LiveReloadProof.json">Live source proof</a><a href="Batch5-ControlProof.json">Controls and restoration</a><a href="Batch5-Costs.json">Material statistics</a><a href="Batch5-Gate.exit.json">Focused generation gate</a><a href="Batch5-Verification.json">Independent reconciliation</a></p><main>'''
    (OUTPUT / 'Batch5-Gallery.html').write_text(page + '\n'.join(cards) + '</main>', encoding='utf-8')
    (OUTPUT / 'Batch5-Sources.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    sheet.save(OUTPUT / 'Batch5-ContactSheet-TAA.png')
    print(OUTPUT / 'Batch5-Gallery.html')


if __name__ == '__main__':
    main()
