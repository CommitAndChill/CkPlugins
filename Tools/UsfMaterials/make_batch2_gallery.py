"""Present ungraded batch-two Unreal captures and source attribution."""
from pathlib import Path
import html
import json
from PIL import Image, ImageDraw, ImageFont
from capture_batch2 import LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
LABELS = ['Fine cotton / poplin', 'Suede', 'Terracotta floor tile', 'Polished marble', 'Hard rubber', 'Clear glass']


def main():
    manifest = json.loads((ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch2Textures/Manifest.json').read_text())
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 19)
    sheet = Image.new('RGB', (1440, 1170), '#171b22')
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 12), 'CkUsf mixed material library / batch 2', fill='white', font=font)
    draw.text((20, 45), 'Actual Unreal captures / original studio lights / temporary TAA / no color grading', fill='#b8c4d6', font=font)
    cards = []
    for index, (name, label) in enumerate(zip(LOOKS, LABELS)):
        filename = f'Batch2-Preview-{name}-Close.png'
        image = Image.open(OUTPUT / filename).convert('RGB')
        x, y = (index % 3) * 480, 85 + (index // 3) * 540
        sheet.paste(image.crop((145, 45, 609, 550)), (x + 8, y + 28))
        draw.text((x + 12, y), label, fill='white', font=font)
        links = ' '.join(f'<a href="Batch2-Preview-{name}-{view}.png">{view}</a>' for view in ['Close', 'Macro', 'Gameplay'])
        baseline = ' '.join(f'<a href="Batch2-{name}-{view}.png">{view} native AA</a>' for view in ['Close', 'Macro', 'Gameplay'])
        record = next(value for value in manifest['materials'].values() if value['look_id'] == name)
        source = record.get('asset_url', record.get('source_url', ''))
        attribution = f'<a href="{html.escape(source)}">CC0 source</a>' if source else '<a href="Batch2-Sources.json">Source manifest</a>'
        cards.append(f'<article><h2>{label}</h2><a href="{filename}"><img src="{filename}" alt="{label} actual Unreal render"></a><p>{links}</p><p>{baseline}</p>{attribution}</article>')
    page = '''<!doctype html><meta charset="utf-8"><title>CkUsf library / batch 2</title>
<style>body{font:16px system-ui;background:#171b22;color:#e7edf6;margin:32px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#222a35;padding:16px;border-radius:12px}img{width:100%}a{color:#9dcbff;margin-right:10px}h2{font-size:22px}</style>
<h1>CkUsf mixed material library / batch 2</h1><p>Actual ungraded Unreal game-viewport captures. Original shader ball and studio lights. Cards use temporary TAA/100%; native AA=0/screen percentage87 captures are linked separately. All values are restored after preview.</p>
<p>Each material samples its own licensed texture data in .ush. Glass uses normal/roughness with authored near-neutral transmission; a diffuse base-color map is not required for clear glass. Thin-surface transmission and screen-space distortion do not trace the ball's thickness. Suede uses native Cloth fuzz, not volumetric scattering.</p>
<p><a href="Batch1-Gallery.html">Batch 1</a><a href="Batch2-Sources.json">Exact source manifest</a><a href="Batch2-LiveReloadProof.json">Live source proof</a><a href="Batch2-ControlProof.json">Control response and restoration</a><a href="Batch2-Costs.json">Material statistics</a><a href="Batch2-Gate.exit.json">Fresh focused gate</a></p><main>'''
    pane = '''</main><h2>Flat-pane transmission inspection</h2><p>Temporary reference panel uses the same live glass MID over the existing tile material. One side is uncovered. IOR=1 isolates transmission from screen-space distortion; the dimmed diagnostic sets transmission to .2. Overrides are restored and the temporary actor is removed. This is thin-surface glass, not traced solid optics.</p><a href="Batch2-GlassPane-Clear.png">Clear pane</a><a href="Batch2-GlassPane-Dimmed.png">Dimmed diagnostic</a>'''
    (OUTPUT / 'Batch2-Gallery.html').write_text(page + '\n'.join(cards) + pane, encoding='utf-8')
    (OUTPUT / 'Batch2-Sources.json').write_text(json.dumps(manifest, indent=2))
    sheet.save(OUTPUT / 'Batch2-ContactSheet-TAA.png')
    print(OUTPUT / 'Batch2-Gallery.html')


if __name__ == '__main__':
    main()
