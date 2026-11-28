"""Present ungraded batch-three Unreal captures and source attribution."""
from pathlib import Path
import argparse
import html
import json
from PIL import Image, ImageDraw, ImageFont
from capture_batch3 import LOOKS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
LABELS = ['Velvet', 'Finished walnut', 'Polished granite', 'Satin brass', 'Frosted glass', 'Carbon fiber']


def frost_section(path):
    """Optional descriptor: {proof: filename, captures: [{label, path}]}.

    Proof JSON uses passed/restored/source_sha256. Only the independent verifier
    evaluates those claims; this gallery presents available artifacts.
    """
    explanation = ('The glass shader averages 64 linear-HDR SceneColor taps through '
        'SurfaceSceneColor.ush. This is a screen-space rough-transmission approximation, '
        'not traced thickness or physically thick optics. Normal/roughness finish data '
        'comes from the clean matte Plastic010 source, not an optical glass scan.')
    section = '<h2>Flat-pane transmission evidence</h2><p>' + explanation + '</p>'
    if not path.exists():
        return section + '<p>New pane captures/proof are pending. No pane result is claimed here.</p>'
    descriptor = json.loads(path.read_text(encoding='utf-8-sig'))
    links = []
    for record in descriptor.get('captures', []):
        image = OUTPUT / record['path']
        if image.is_file():
            relative = image.resolve().relative_to(OUTPUT.resolve()).as_posix()
            label = html.escape(record.get('label', relative))
            url = html.escape(relative, quote=True)
            if record.get('label') in ['TAA-Close-Control', 'TAA-Close-Blurred']:
                links.append(f'<figure style="display:inline-block;width:45%;margin:1%"><figcaption>{label}</figcaption><a href="{url}"><img src="{url}" alt="{label}"></a></figure>')
            else:
                links.append(f'<a href="{url}">{label}</a>')
    proof = OUTPUT / descriptor['proof'] if descriptor.get('proof') else None
    if proof is not None and proof.is_file():
        relative = proof.resolve().relative_to(OUTPUT.resolve()).as_posix()
        links.append(f'<a href="{html.escape(relative, quote=True)}">Pane proof record</a>')
    note = html.escape(descriptor.get('scope', 'Linked artifacts require independent evidence verification; user visual acceptance is separate.'))
    return section + '<p>' + note + '</p><div>' + (' '.join(links) or 'No available pane artifacts are referenced.') + '</div>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frost-evidence', type=Path, default=OUTPUT / 'Batch3-FrostEvidence.json',
                        help='Optional pane descriptor JSON; relative paths resolve under Saved/UsfMaterialGallery')
    args = parser.parse_args()
    frost_path = args.frost_evidence if args.frost_evidence.is_absolute() else OUTPUT / args.frost_evidence
    manifest = json.loads((ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch3Textures/Manifest.json').read_text())
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 19)
    sheet = Image.new('RGB', (1440, 1170), '#171b22')
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 12), 'CkUsf mixed material library / batch 3', fill='white', font=font)
    draw.text((20, 45), 'Saved Unreal viewport captures / cropped contact sheet / original files linked', fill='#b8c4d6', font=font)
    cards = []
    for index, (name, label) in enumerate(zip(LOOKS, LABELS)):
        filename = f'Batch3-Preview-{name}-Close.png'
        image = Image.open(OUTPUT / filename).convert('RGB')
        x, y = (index % 3) * 480, 85 + (index // 3) * 540
        sheet.paste(image.crop((145, 45, 609, 550)), (x + 8, y + 28))
        draw.text((x + 12, y), label, fill='white', font=font)
        links = ' '.join(f'<a href="Batch3-Preview-{name}-{view}.png">{view}</a>' for view in ['Close', 'Macro', 'Gameplay'])
        baseline = ' '.join(f'<a href="Batch3-{name}-{view}.png">{view} native AA</a>' for view in ['Close', 'Macro', 'Gameplay'])
        record = next(value for value in manifest['materials'].values() if value['look_id'] == name)
        source = record.get('asset_url', record.get('source_url', ''))
        attribution = f'<a href="{html.escape(source, quote=True)}">CC0 source</a>' if source else '<a href="Batch3-Sources.json">Source manifest</a>'
        provenance = html.escape(record.get('identity_notes', 'See exact source manifest for material identity and modifications.'))
        cards.append(f'<article><h2>{label}</h2><a href="{filename}"><img src="{filename}" alt="{label} saved Unreal render"></a><p>{links}</p><p>{baseline}</p>{attribution}<p>{provenance}</p></article>')
    page = '''<!doctype html><meta charset="utf-8"><title>CkUsf library / batch 3</title>
<style>body{font:16px system-ui;background:#171b22;color:#e7edf6;margin:32px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#222a35;padding:16px;border-radius:12px}img{width:100%}a{color:#9dcbff;margin-right:10px}h2{font-size:22px}</style>
<h1>CkUsf mixed material library / batch 3</h1><p>Saved Unreal game-viewport captures. Contact-sheet images are cropped for layout; original captures are linked. Preview and native capture filenames are separated below. Actual capture settings and final state restoration are evidence to verify, not claims inferred from these filenames.</p>
<p>Every showcased material remains authored through .ush. Velvet uses actual velvet data and Cloth fuzz; walnut and carbon fiber use the supported coat response. Brass reflectance is authored independently over steel-source machining detail. Frosted glass uses the scoped SceneColor extension for a 64-tap linear-HDR screen-space approximation. No thick optics or renderer-wide acceptance is implied.</p>
<p><a href="Batch1-Gallery.html">Batch 1</a><a href="Batch2-Gallery.html">Batch 2</a><a href="Batch3-Sources.json">Exact source manifest</a><a href="Batch3-LitCaptures.json">Capture records</a><a href="Batch3-LiveReloadProof.json">Live source proof</a><a href="Batch3-ControlProof.json">Control response and restoration</a><a href="Batch3-Costs.json">Material statistics</a><a href="Batch3-Gate.exit.json">Focused gate record</a><a href="Batch3-Verification.json">Independent reconciliation</a></p><main>'''
    pane = '</main>' + frost_section(frost_path)
    (OUTPUT / 'Batch3-Gallery.html').write_text(page + '\n'.join(cards) + pane, encoding='utf-8')
    (OUTPUT / 'Batch3-Sources.json').write_text(json.dumps(manifest, indent=2))
    sheet.save(OUTPUT / 'Batch3-ContactSheet-TAA.png')
    print(OUTPUT / 'Batch3-Gallery.html')


if __name__ == '__main__':
    main()
