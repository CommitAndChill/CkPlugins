"""Present original batch-four Unreal captures and recorded material identities without grading."""
from pathlib import Path
import html
import json
from PIL import Image, ImageDraw, ImageFont
from capture_batch4 import LOOKS


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
LABELS = ['Knitted fabric', 'Patent leather', 'Porcelain-style glazed tile', 'Terrazzo', 'Translucent plastic', 'Cork']


def specialty_section():
    section = '<h2>Independent material controls</h2><p>Translucent plastic uses a thin-surface approximation with a plastic-only local 80 cd Point fill. BodyCoverage is lit body coverage over thin transmission, not a measured volume-scattering coefficient or thickness-aware volume scattering. This batch does not enable SceneColor sampling by default. The fill bounds record covers the other library specimen meshes; dedicated neighbor captures inspect rendered light isolation. Porcelain-style glaze and matte grout require source-aligned masking; the catalog name alone does not verify chemical composition.</p>'
    for filename, label in [('Batch4-PlasticProof.json', 'Plastic transmission and body coverage'),
                            ('Batch4-PorcelainProof.json', 'Glaze and grout separation'),
                            ('Batch4-FillProof.json', 'Local fill isolation and restoration'),
                            ('Batch4-FillBounds.json', 'Local fill bounds')]:
        if (OUTPUT / filename).is_file():
            section += f'<p><a href="{filename}">{label}: dedicated proof record</a></p>'
        else:
            section += f'<p>{label}: dedicated proof pending.</p>'
    return section


def main():
    manifest = json.loads((ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch4Textures/Manifest.json').read_text(encoding='utf-8'))
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 19)
    sheet = Image.new('RGB', (1440, 1170), '#171b22')
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 12), 'CkUsf mixed material library / batch 4', fill='white', font=font)
    draw.text((20, 45), 'Saved Unreal captures / cropped contact sheet / original files linked', fill='#b8c4d6', font=font)
    cards = []
    for index, (name, label) in enumerate(zip(LOOKS, LABELS)):
        filename = f'Batch4-Preview-{name}-Close.png'
        image = Image.open(OUTPUT / filename).convert('RGB')
        width, height = image.size
        crop = image.crop((int(width * .18), int(height * .08), int(width * .81), int(height * .98)))
        crop.thumbnail((464, 505), Image.Resampling.LANCZOS)
        x, y = (index % 3) * 480, 85 + (index // 3) * 540
        sheet.paste(crop, (x + (480 - crop.width) // 2, y + 28))
        draw.text((x + 12, y), label, fill='white', font=font)
        links = ' '.join(f'<a href="Batch4-Preview-{name}-{view}.png">{view}</a>' for view in ['Close', 'Macro', 'Gameplay'])
        baseline = ' '.join(f'<a href="Batch4-{name}-{view}.png">{view} native AA</a>' for view in ['Close', 'Macro', 'Gameplay'])
        record = next(value for value in manifest['materials'].values() if value['look_id'] == name)
        source = record.get('asset_url', record.get('source_url', ''))
        attribution = f'<a href="{html.escape(source, quote=True)}">Recorded source</a>' if source else '<a href="Batch4-Sources.json">Source manifest</a>'
        provenance = html.escape(record.get('identity_notes', 'See the source manifest for material identity, license and modifications.'))
        cards.append(f'<article><h2>{label}</h2><a href="{filename}"><img src="{filename}" alt="{label} saved Unreal render"></a><p>{links}</p><p>{baseline}</p>{attribution}<p>{provenance}</p></article>')
    page = '''<!doctype html><meta charset="utf-8"><title>CkUsf library / batch 4</title>
<style>body{font:16px system-ui;background:#171b22;color:#e7edf6;margin:32px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#222a35;padding:16px;border-radius:12px}img{width:100%}a{color:#9dcbff;margin-right:10px}h2{font-size:22px}</style>
<h1>CkUsf mixed material library / batch 4</h1><p>Saved Unreal game-viewport captures. The contact sheet is cropped and resized for layout; original captures are linked. Preview/native filenames distinguish capture passes. Their actual settings and final restoration are checked by the evidence reconciliation.</p>
<p>Every material stays authored through .ush. Knit uses Cloth fuzz; patent leather and porcelain-style tile use the supported ClearCoat response. Terrazzo and cork retain dielectric surface responses. Translucent plastic uses native thin-surface transmission with independently controlled lit body coverage.</p>
<p><a href="Batch1-Gallery.html">Batch 1</a><a href="Batch2-Gallery.html">Batch 2</a><a href="Batch3-Gallery.html">Batch 3</a><a href="Batch4-Sources.json">Exact source manifest</a><a href="Batch4-LitCaptures.json">Capture records</a><a href="Batch4-LiveReloadProof.json">Live source proof</a><a href="Batch4-ControlProof.json">Controls and restoration</a><a href="Batch4-Costs.json">Material statistics</a><a href="Batch4-Gate.exit.json">Focused generation gate</a><a href="Batch4-Verification.json">Independent reconciliation</a></p><main>'''
    (OUTPUT / 'Batch4-Gallery.html').write_text(page + '\n'.join(cards) + '</main>' + specialty_section(), encoding='utf-8')
    (OUTPUT / 'Batch4-Sources.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    sheet.save(OUTPUT / 'Batch4-ContactSheet-TAA.png')
    print(OUTPUT / 'Batch4-Gallery.html')


if __name__ == '__main__':
    main()
