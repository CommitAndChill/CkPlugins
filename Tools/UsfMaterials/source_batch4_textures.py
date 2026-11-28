"""Reproduce the approved fourth CC0 material source batch without Unreal.

Requires sibling source_batch2_textures.py, Pillow and NumPy. Publisher files
and generated receipts are immutable: cached re-runs verify, never overwrite.
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
DEFAULT = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch4Textures'
SELECTION = {
    'knit': ('LibraryKnit', 'Fabric085', 'knit',
             'Actual wool fabric with visually inspected repeating interlocking yarn loops. No procedural weave or added wear. Source maps cannot produce geometric yarn silhouette alone.'),
    'patent_leather': ('LibraryPatentLeather', 'Leather026', 'patent_leather',
                       'Actual smooth black leather grain reused beneath an independently authored high-gloss patent coating. Not a measured patent-leather coating scan; source roughness describes underlying leather.'),
    'porcelain': ('LibraryPorcelain', 'Tiles133A', 'porcelain',
                  'Actual clean white square ceramic-style tile and grout layout. Porcelain-finish ceramic: porcelain composition is unverified by the official tile catalog. No invented tile grid; glaze exclusion follows the aligned source color.'),
    'terrazzo': ('LibraryTerrazzo', 'Terrazzo013', 'terrazzo',
                 'Actual clean intact multicolor terrazzo aggregate source. No procedural chips, cracks or added aging.'),
    'translucent_plastic': ('LibraryTranslucentPlastic', 'Plastic010', 'translucent_plastic_clean',
                            'Actual clean smooth white plastic microfinish and source color. Transmission/tint are independently authored; source does not measure optical thickness, scattering or transmission. Rejected Plastic013A/Plastic006 candidates are retained separately and not used.'),
    'cork': ('LibraryCork', 'Cork004', 'cork',
             'Actual clean beige compressed cork granules with aligned pore and color data. No added noise or wear; source does not certify a particular binder or density.'),
}


def source_one(item, output, pins):
    key, (look, asset, storage_key, notes) = item
    # Storage key differs for plastic so rejected candidate maps remain untouched.
    record = source.ambient_source(output, storage_key, look, asset, None)
    if not {'BaseColor', 'Normal', 'Roughness'}.issubset(record['maps']):
        raise RuntimeError('Missing required aligned source maps: ' + key)
    sizes = {(entry['width'], entry['height']) for entry in record['maps'].values()}
    if sizes != {(1024, 1024)}:
        raise RuntimeError('Expected aligned 1024-square maps: ' + key)
    if pins:
        previous = pins['materials'][key]
        if record['archive']['sha256'] != previous['archive']['sha256']:
            raise RuntimeError('Pinned archive differs: ' + key)
        for channel, entry in record['maps'].items():
            if entry['sha256'] != previous['maps'][channel]['sha256']:
                raise RuntimeError('Pinned source map differs: ' + key + '/' + channel)
    record.update(look_id=look, asset_id=asset, provider='ambientcg', license='CC0-1.0', identity_notes=notes)
    return key, record


def tile_mask(output, record):
    info = record['maps']['BaseColor']
    image = source.Image.open(output / info['path']).convert('RGB')
    # Actual grout is darker than every tile interior. Thresholds were selected
    # after inspecting aligned source BC/N/R/height, not from an unrelated grid.
    value = source.np.asarray(image, dtype=source.np.float64).mean(axis=2) / 255.0
    t = source.np.clip((value - 0.70) / 0.10, 0.0, 1.0)
    mask = source.np.rint(255.0 * t * t * (3.0 - 2.0 * t)).astype(source.np.uint8)
    buffer = io.BytesIO()
    source.Image.fromarray(mask).save(buffer, format='PNG', compress_level=9)
    record['maps']['TileMask'] = source.save_map(output, 'porcelain', record['look_id'], 'TileMask', buffer.getvalue(), {
        'modifications': 'Derived source-aligned segmentation: c=mean(decoded sRGB BaseColor RGB)/255; t=clamp((c-0.70)/0.10,0,1); mask=round(255*t*t*(3-2*t)). No spatial grid, new grain or source-map modification.',
        'source_sha256': info['sha256'], 'source_path': info['path'],
        'usage': 'R=tile/glaze coverage, 1 tile, 0 grout. Linear data; multiply coating coverage by R. Texture shares original source UVs.',
        'coverage_mean': float(mask.mean() / 255.0),
        'coverage_above_half': float((mask >= 128).mean()),
    })


def sheet(output, materials, detail=False):
    canvas = source.Image.new('RGB', (1536, 4 * 286), (30, 30, 34))
    draw = source.ImageDraw.Draw(canvas)
    for column, key in enumerate(SELECTION):
        for row, channel in enumerate(['BaseColor', 'Normal', 'Roughness', 'TileMask']):
            x, y = column * 256, row * 286
            draw.text((x + 4, y + 5), key + '/' + channel, fill='white')
            if channel not in materials[key]['maps']:
                draw.text((x + 4, y + 50), 'No invented mask', fill=(160, 160, 160))
                continue
            image = source.Image.open(output / materials[key]['maps'][channel]['path'])
            if image.mode in {'I', 'I;16', 'I;16B', 'I;16L'}:
                image = source.Image.fromarray(source.np.rint(source.np.asarray(image, dtype=float) / 257).astype(source.np.uint8))
            if detail:
                w, h = image.size
                image = image.crop((w // 2 - 128, h // 2 - 128, w // 2 + 128, h // 2 + 128))
            image = image.convert('RGB').resize((256, 256), source.Image.Resampling.NEAREST if detail else source.Image.Resampling.LANCZOS)
            canvas.paste(image, (x, y + 25))
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
    tile_mask(output, materials['porcelain'])
    materials['translucent_plastic']['finish_contract'] = 'BC/N/R retained and available; native thin transmission/tint is separately authored. No optical scan, scene-copy blur or measured body-coverage claim.'
    materials['patent_leather']['finish_contract'] = 'Texture describes leather substrate; high-gloss dielectric coating is independently authored. Preserve leather/grain alignment and do not claim scanned patent roughness.'
    sheet(output, materials)
    sheet(output, materials, detail=True)
    helper = Path(source.__file__).resolve()
    manifest = {
        'schema_version': 1, 'retrieved_utc': pins['retrieved_utc'] if pins else datetime.now(timezone.utc).isoformat(),
        'generator_source': 'Tools/UsfMaterials/source_batch4_textures.py', 'generator_sha256': source.sha256(Path(__file__).read_bytes()),
        'required_helper': helper.relative_to(ROOT).as_posix(), 'required_helper_sha256': source.sha256(helper.read_bytes()),
        'maps_root': 'Plugins/CkTests/Resources/CkUsf/Batch4Textures',
        'licenses': [{'provider': 'ambientcg', 'spdx': 'CC0-1.0', 'url': license_url, 'path': license_path.relative_to(output).as_posix(), 'sha256': source.sha256(license_data)}],
        'materials': materials,
        'runtime_channels': {'default': ['BaseColor', 'Normal', 'Roughness'], 'porcelain_extra': ['TileMask']},
        'verification_scope': 'Official license/metadata; publisher ZIP size and CRC, SHA256 pins, aligned 1024-square PNGs, decoded channel distributions and boundary steps. Source overview/detail sheets inspected separately. No editor import, runtime rendering, optical calibration or artistic approval is claimed.',
        'retained_candidates': {'Plastic013A': 'Rejected visible handling marks in roughness; retained translucent_plastic maps and archive.', 'Plastic006': 'Rejected visible scuffs and streaks; retained plastic_candidate maps and archive.'},
    }
    source.immutable(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({key: {'asset': value['asset_id'], 'look_id': value['look_id'], 'maps': {c: [i['width'], i['height']] for c, i in value['maps'].items()}} for key, value in materials.items()}, indent=2))
    print('Manifest SHA256', source.sha256(manifest_path.read_bytes()))


if __name__ == '__main__':
    main()
