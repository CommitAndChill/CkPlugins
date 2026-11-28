"""Source the fifth approved CC0 material batch without importing into Unreal.

Requires sibling source_batch2_textures.py, Pillow and NumPy. Original source
archives/maps, license and metadata are immutable; cached runs verify SHA256
pins. No synthetic grain, source recoloring or resampling is performed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import source_batch2_textures as source

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch5Textures'
SELECTION = {
    'denim': ('LibraryDenim', 'Fabric069',
              'Actual blue jeans fabric with visually inspected diagonal twill threads in the aligned color/normal detail. Not generic canvas, no invented weave or additional wear. Texture maps do not create geometric thread silhouette.'),
    'concrete': ('LibraryConcrete', 'Concrete048',
                 'Actual clean smooth concrete surface with subtle formed texture and pores. No added cracks, damage or aging. Source physical coverage is unspecified; do not infer a calibrated mix or strength.'),
    'brick': ('LibraryBrick', 'Bricks104',
              'Actual clean red/orange brick and mortar masonry. Original aligned1024x512 aspect is retained; both dimensions are power-of-two. Source surface variation is not a claim of perfectly manufactured brick dimensions. No unrelated procedural mortar grid.'),
    'stainless_steel': ('LibraryStainlessSteel', 'Metal049A',
                        'Actual authored clean neutral silver-colored bare-metal microfinish, not a certified stainless-alloy scan. No rust or wear overlay. Source roughness is low; satin roughness and neutral stainless-steel reflectance must be independently authored. Source BaseColor may supply restrained finish variation rather than an alloy calibration.'),
    'plywood': ('LibraryPlywood', 'Wood089',
                'Actual authored plywood SIDE/edge texture with alternating veneer layers. This set represents layered cut edges, not the outer veneer face. Do not claim a measured ply count, adhesive or face veneer species.'),
    'cardboard': ('LibraryCardboard', 'Cardboard002',
                  'Actual clean brown cardboard with unprinted paper fibers and subtle aligned corrugation. No shipping labels, printed marks, added folds or generic-noise replacement. This surface set does not model a corrugated cut-edge cross-section.'),
}


def source_one(item, output, pins):
    key, (look, asset, notes) = item
    record = source.ambient_source(output, key, look, asset, pins)
    required = {'BaseColor', 'Normal', 'Roughness'}
    if not required.issubset(record['maps']):
        raise RuntimeError('Missing required aligned source maps: ' + key)
    expected_size = (1024, 512) if key == 'brick' else (1024, 1024)
    for channel, entry in record['maps'].items():
        if (entry['width'], entry['height']) != expected_size:
            raise RuntimeError('Source map dimensions/aspect differ: ' + key + '/' + channel)
        if pins and entry['sha256'] != pins['materials'][key]['maps'][channel]['sha256']:
            raise RuntimeError('Pinned source map differs: ' + key + '/' + channel)
    record.update(look_id=look, asset_id=asset, provider='ambientcg', license='CC0-1.0', identity_notes=notes)
    record['transform_provenance'] = 'None. Publisher PNG bytes, source aspect and alignment retained; no color, normal, roughness or UV transformation baked into maps.'
    return key, record


def sheet(output, materials, detail=False):
    canvas = source.Image.new('RGB', (1536, 4 * 286), (30, 30, 34))
    draw = source.ImageDraw.Draw(canvas)
    for column, key in enumerate(SELECTION):
        for row, channel in enumerate(['BaseColor', 'Normal', 'Roughness', 'Height']):
            x, y = column * 256, row * 286
            draw.text((x + 4, y + 5), key + '/' + channel, fill='white')
            if channel not in materials[key]['maps']:
                draw.text((x + 4, y + 60), 'Not provided', fill=(160, 160, 160))
                continue
            image = source.Image.open(output / materials[key]['maps'][channel]['path'])
            if image.mode in {'I', 'I;16', 'I;16B', 'I;16L'}:
                image = source.Image.fromarray(source.np.rint(source.np.asarray(image, dtype=float) / 257).astype(source.np.uint8))
            if detail:
                w, h = image.size
                image = image.crop((w // 2 - 128, h // 2 - 128, w // 2 + 128, h // 2 + 128))
            image = image.convert('RGB')
            # Overview preserves the publisher's2:1 brick aspect; a gray gutter
            # identifies the unused space instead of stretching the tile layout.
            image.thumbnail((256, 256), source.Image.Resampling.NEAREST if detail else source.Image.Resampling.LANCZOS)
            canvas.paste(image, (x + (256 - image.width) // 2, y + 25 + (256 - image.height) // 2))
    buffer = io.BytesIO()
    canvas.save(buffer, format='PNG', compress_level=9)
    source.immutable(output / ('SourceDetailContactSheet.png' if detail else 'SourceMapContactSheet.png'), buffer.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = output / 'Manifest.json'
    pins = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    license_url = 'https://docs.ambientcg.com/license/'
    license_path = output / 'License/ambientcg.html'
    license_data = source.cached(license_path, license_url)
    if b'CC0' not in license_data:
        raise RuntimeError('Official license snapshot lacks CC0 statement')
    with ThreadPoolExecutor(max_workers=3) as pool:
        materials = dict(pool.map(lambda item: source_one(item, output, pins), SELECTION.items()))
    materials['brick']['mask_note'] = 'No extra mask required or fabricated; actual BC/Normal/Roughness retain the aligned mortar layout. A future mortar-specific control requires a source-aligned segmentation receipt.'
    materials['stainless_steel']['finish_contract'] = 'Keep bare-metal response and clean default. Source alloy is unspecified; author neutral stainless reflectance and satin roughness independently. No circular direction field or invented tangent map is supplied.'
    sheet(output, materials)
    sheet(output, materials, detail=True)
    helper = Path(source.__file__).resolve()
    manifest = {
        'schema_version': 1, 'retrieved_utc': pins['retrieved_utc'] if pins else datetime.now(timezone.utc).isoformat(),
        'generator_source': 'Tools/UsfMaterials/source_batch5_textures.py', 'generator_sha256': source.sha256(Path(__file__).read_bytes()),
        'required_helper': helper.relative_to(ROOT).as_posix(), 'required_helper_sha256': source.sha256(helper.read_bytes()),
        'maps_root': 'Plugins/CkTests/Resources/CkUsf/Batch5Textures',
        'licenses': [{'provider': 'ambientcg', 'spdx': 'CC0-1.0', 'url': license_url, 'path': license_path.relative_to(output).as_posix(), 'sha256': source.sha256(license_data)}],
        'materials': materials,
        'runtime_channels': ['BaseColor', 'Normal', 'Roughness'],
        'runtime_texture_count': 18,
        'verification_scope': 'Official metadata and CC0 license snapshot; publisher ZIP size/CRC; source SHA256 pins; aligned dimensions, original aspect, decoded distributions and boundary steps; source overview/detail sheets. No editor import, rendered quality, optical calibration, certified alloy or artistic acceptance is claimed.',
        'source_limits': 'Stainless-steel reflectance/satin finish are independently authored over neutral bare-metal source microfinish. Plywood source depicts a layered cut edge, not the outer face. Publisher gives zero/unspecified physical dimensions for these selected assets; no physical coverage is invented.',
    }
    source.immutable(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({key: {'asset': value['asset_id'], 'look_id': value['look_id'], 'maps': {c: [i['width'], i['height']] for c, i in value['maps'].items()}} for key, value in materials.items()}, indent=2))
    print('Manifest SHA256', source.sha256(manifest_path.read_bytes()))


if __name__ == '__main__':
    main()
