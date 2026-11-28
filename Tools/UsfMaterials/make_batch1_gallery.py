"""Assemble ungraded Unreal capture evidence into a labeled comparison sheet and local gallery."""
from pathlib import Path
import html
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
ROWS = [
    ('LibrarySilk', 'Crepe satin silk', 'Authored weave, rotation and anisotropy', 'https://polyhaven.com/a/crepe_satin'),
    ('LibraryLeather', 'Pebbled leather', 'Grain, pores and correlated roughness', 'https://ambientcg.com/a/Leather037'),
    ('LibraryTile', 'Glazed ceramic tile', 'Reflective glaze / matte contrasting grout', 'https://ambientcg.com/a/Tiles032'),
    ('LibraryOak', 'Finished oak', 'Oak grain and pores beneath a finish', 'https://ambientcg.com/a/Wood049'),
    ('LibraryAluminum', 'Linear-brushed aluminum', 'Coherent parallel machining; independently authored aluminum reflectance', 'https://ambientcg.com/a/Metal009'),
    ('LibraryPlastic', 'Matte molded plastic', 'Fine authored detail, dielectric reflection', 'https://ambientcg.com/a/Plastic013A')]


def main():
    font_path = 'C:/Windows/Fonts/segoeui.ttf'
    title = ImageFont.truetype(font_path, 25)
    small = ImageFont.truetype(font_path, 17)
    sheet = Image.new('RGB', (1440, 1170), '#171b22')
    draw = ImageDraw.Draw(sheet)
    draw.text((24, 13), 'CkUsf material library / batch 1', fill='white', font=title)
    draw.text((24, 48), 'Actual Unreal renders | temporary TAA preview | original studio lights | no color grading', fill='#b8c4d6', font=small)
    cards = []
    for index, (name, label, detail, source) in enumerate(ROWS):
        image_path = OUTPUT / ('Aluminum-Refined-Close.png' if name == 'LibraryAluminum'
                               else f'Batch1-Preview-{name}-Close.png')
        image = Image.open(image_path).convert('RGB')
        x, y = (index % 3) * 480, 85 + (index // 3) * 540
        # Crop presentation borders only; do not alter rendered pixels or material colors.
        crop = image.crop((145, 45, 609, 550))
        sheet.paste(crop, (x + 8, y + 28))
        draw.text((x + 12, y), label, fill='white', font=small)
        links = ' '.join(f'<a href="Batch1-{name}-{view}.png">{view} baseline</a>' for view in ['Close', 'Macro', 'Gameplay'])
        preview_links = ' '.join(f'<a href="Batch1-Preview-{name}-{view}.png">{view} TAA</a>' for view in ['Close', 'Macro', 'Gameplay'])
        if name == 'LibraryAluminum':
            links = '<a href="Aluminum-Diagnosis-Baseline.png">Original circular finish</a>'
            preview_links = ' '.join(f'<a href="Aluminum-Refined-{view}.png">{view} revised TAA</a>' for view in ['Close', 'Macro', 'Gameplay'])
            detail += '. CC0 Metal009 brushed-steel normal/roughness reused as machining data; neutral Metal051A base color. This is an authored aluminum finish, not a scanned aluminum set.'
        cards.append(f'<article><h2>{html.escape(label)}</h2><p>{html.escape(detail)}</p><a href="{image_path.name}"><img src="{image_path.name}" alt="{html.escape(label)} actual Unreal TAA preview"></a><p>{links}</p><p>{preview_links}</p><a href="{source}">CC0 texture source</a></article>')
    sheet.save(OUTPUT / 'Batch1-ContactSheet-TAA.png')
    page = '''<!doctype html><meta charset="utf-8"><title>CkUsf library - batch 1</title>
<style>body{font:16px system-ui;background:#171b22;color:#e7edf6;margin:32px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#222a35;padding:16px;border-radius:12px}img{width:100%}a{color:#9dcbff;margin-right:10px}h2{font-size:22px}</style>
<h1>CkUsf material library / batch 1</h1><p>Actual Unreal renders, clean/intact defaults. The cards show a temporary TAA/100% preview using the original studio lights. Project AA=0 and screen percentage=87 were restored; baseline captures are linked separately. No color grading or generated substitute images.</p>
<p>Silk and aluminum use direction maps. Current Substrate Rect direct lighting ignores anisotropy, while environment reflections respond to it. Aluminum was revised after circular direction cells produced large reflection patches; its parallel machining and coherent direction now preserve the form. This is a technical/art review batch, not user artistic acceptance.</p>
<p><a href="Aluminum-BeforeAfter.png">Aluminum before / after</a><a href="Aluminum-LiveReloadProof.json">Revised aluminum live-edit proof</a><a href="Batch1-Aluminum.exit.json">Focused generation check</a></p>
<p><a href="Batch1-LiveReloadProof.json">Six-look live reload proof</a><a href="Batch1-DirectionalProof.json">Directional proof</a><a href="Batch1-Costs.json">Material statistics</a><a href="Batch1-Test.exit.json">Full run:56 passed/1 DDC crash</a><a href="Batch1-ToonRetry.exit.json">Unchanged isolated retry:1/1 passed</a></p><main>'''
    page += '\n'.join(cards) + '</main>'
    page += '<h2>Initial batch compatible-light diagnostic</h2><p>Historical captures from before the aluminum revision. Temporary point light, 60 cd. Material normal and roughness variation are neutralized for this comparison; these are diagnostic overrides, not the ordinary studio defaults. All overrides and studio lights were restored.</p>'
    for name in ['LibrarySilk', 'LibraryAluminum']:
        page += f'<h3>{name}</h3>' + ''.join(f'<a href="Batch1-Direction-{name}-{stage}.png">{stage}</a>' for stage in ['isotropic', 'axis0', 'axis90'])
    (OUTPUT / 'Batch1-Gallery.html').write_text(page, encoding='utf-8')
    comparison = Image.new('RGB', (1508, 590), '#171b22')
    labels = ImageDraw.Draw(comparison)
    for index, (filename, label) in enumerate([
            ('Aluminum-Diagnosis-Baseline.png', 'Before: circular direction / broken reflection patches'),
            ('Aluminum-Refined-Close.png', 'After: continuous linear brushing')]):
        comparison.paste(Image.open(OUTPUT / filename).convert('RGB'), (index * 754, 40))
        labels.text((index * 754 + 14, 8), label, fill='white', font=small)
    comparison.save(OUTPUT / 'Aluminum-BeforeAfter.png')
    print(OUTPUT / 'Batch1-Gallery.html')


if __name__ == '__main__':
    main()
