"""Reproduce batch-six licensed material sources without Unreal/editor access.

Uses the existing Batch2 image/publisher helpers. A local CGBookcase adapter is
restricted to the selected official asset/map URLs. Original PNGs are retained
unchanged; only the source-aligned mosaic coating mask is derived.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
import source_batch2_textures as source

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch6Textures'
CG_ASSET_URL = 'https://www.cgbookcase.com/textures/galvanized-steel-02'
CG_LICENSE_URL = 'https://www.cgbookcase.com/textures'
CG_ZIP_URL = 'https://cgbookcase-volume.b-cdn.net/t/GalvanizedSteel02_MR_1K.zip'
CG_MAP_ROOT = 'https://cgbookcase.b-cdn.net/textures/thumbnails/GalvanizedSteel02_1K/'
SELECTION = {
    'linen': ('LibraryLinen', 'polyhaven', 'rough_linen', 'linen',
              'Official Rough Linen: actual fine woven crosshatch and irregular/slubby threads. Source identifies linen; no laboratory flax-composition certification. Preserve1024x1026 source aspect; explicitly resize only runtime imports to1024 square for streaming/mips, a0.195% height change.'),
    'smooth_leather': ('LibrarySmoothLeather', 'ambientcg', 'Leather038', 'smooth_leather',
                       'Actual fine smooth orange/brown leather grain, distinct from black patent and coarse pebbled leather. No independently invented pebble pattern, added wear or patent coating.'),
    'mosaic': ('LibraryMosaic', 'ambientcg', 'Tiles071', 'mosaic_clean',
               'Actual intact white hexagonal mosaic with aligned grout. Coating mask derives from source cavity AO; no invented hexagonal grid. Rejected Tiles019 shows visible chips/dirty aged pieces and is retained separately.'),
    'pine': ('LibraryPine', 'polyhaven', 'coated_pine', 'pine',
             'Official Coated Pine, explicitly pine-tagged with real softwood grain and knots. Source includes a varnished finish and light scratches; do not claim pristine raw timber or laboratory species certification. No added aging.'),
    'limestone': ('LibraryLimestone', 'ambientcg', 'Tiles139', 'limestone',
                  'Official limestone-tagged beige/cream fine-stone tiles with subtle source spotting and slightly-worn catalog tag. Intact slab layout, not granite, and no added damage. Geological chemistry/grade is not independently measured.'),
    'galvanized_steel': ('LibraryGalvanizedSteel', 'cgbookcase', 'GalvanizedSteel02', 'galvanized_steel',
                        'Official Galvanized Steel02 with actual authored zinc-spangle cells aligned in color/roughness/height; original DirectX normal includes fine finish streaks. No rust overlay or generic-noise spangle substitute. Not a measured zinc-coating thickness or alloy certification.'),
}


def cg_cached(path, url):
    # This adapter cannot become an arbitrary downloader or expand helper HOSTS.
    allowed = {CG_ASSET_URL, CG_LICENSE_URL}
    allowed.update(CG_MAP_ROOT + 'GalvanizedSteel02_1K_' + channel + '.png'
                   for channel in ['BaseColor', 'Normal', 'Roughness', 'Height', 'AO'])
    if url not in allowed:
        raise RuntimeError('Unexpected CGBookcase URL: ' + url)
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(url, headers={'User-Agent': 'CkMaterialLibrary/1.0'})
    with urllib.request.urlopen(request, timeout=90) as response:
        # Same exact URL only: do not follow an unverified CDN or login redirect.
        if response.url != url:
            raise RuntimeError('Unexpected CGBookcase redirect: ' + response.url)
        data = response.read(10_000_001)
    if len(data) > 10_000_000:
        raise RuntimeError('Selected CGBookcase file exceeds focused limit')
    source.immutable(path, data)
    return data


def cg_source(output, look):
    page_path = output / 'Metadata/GalvanizedSteel02_asset.html'
    page = cg_cached(page_path, CG_ASSET_URL)
    if b'Normal (DirectX)' not in page or b'GalvanizedSteel02_1K_Normal.png' not in page:
        raise RuntimeError('Official asset page does not establish selected DirectX map identity')
    result = {
        'source_url': CG_ASSET_URL, 'author': 'Dorian Zgraggen / CGBookcase',
        'author_source': CG_LICENSE_URL, 'metadata_path': page_path.relative_to(output).as_posix(),
        'metadata_sha256': source.sha256(page), 'official_tags': ['Galvanized Steel02'],
        'coverage_cm': {'x': None, 'y': None}, 'coverage_note': 'No physical coverage specified on the official asset page; do not infer centimeters.',
        'normal_convention_source': 'Official asset Available Maps labels Normal (DirectX); exact referenced1K Normal map is retained unchanged.',
        'download_route': 'Official asset page map-library URLs. These are actual aligned1024-square PNG map images, not rendered sphere previews or query-downscaled images.',
        'unavailable_archive': {'url': CG_ZIP_URL, 'observed_status': 403, 'note': 'Single ZIP request failed; no archive exists or archive hash is claimed. Individual official1K originals are retained and pinned instead.'},
        'download_client_receipt': 'Metadata/GalvanizedSteel02_download_client.js',
        'originals': {}, 'maps': {},
    }
    for channel in ['BaseColor', 'Normal', 'Roughness', 'Height', 'AO']:
        filename = 'GalvanizedSteel02_1K_' + channel + '.png'
        url = CG_MAP_ROOT + filename
        original = output / 'galvanized_steel/Original' / filename
        data = cg_cached(original, url)
        result['originals'][channel] = {'path': original.relative_to(output).as_posix(), 'sha256': source.sha256(data), 'url': url, 'bytes': len(data)}
        result['maps'][channel] = source.save_map(output, 'galvanized_steel', look, channel, data, {
            'source_url': url, 'modifications': 'None; byte-identical official public1K map PNG; officialZIP host403 so map-library route retained.',
        })
    return result


def source_one(item, output, pins):
    key, (look, provider, asset, storage_key, notes) = item
    if provider == 'ambientcg':
        record = source.ambient_source(output, storage_key, look, asset, None)
    elif provider == 'polyhaven':
        record = source.poly_source(output, storage_key, look, asset, None)
    else:
        record = cg_source(output, look)
    if not {'BaseColor', 'Normal', 'Roughness'}.issubset(record['maps']):
        raise RuntimeError('Missing actual source maps: ' + key)
    expected_size = (1024, 1026) if key == 'linen' else (1024, 1024)
    for channel, entry in record['maps'].items():
        if (entry['width'], entry['height']) != expected_size:
            raise RuntimeError('Source map size/alignment differs: ' + key + '/' + channel)
        if pins and entry['sha256'] != pins['materials'][key]['maps'][channel]['sha256']:
            raise RuntimeError('Pinned source map differs: ' + key + '/' + channel)
    if pins and 'archive' in record and record['archive']['sha256'] != pins['materials'][key]['archive']['sha256']:
        raise RuntimeError('Pinned archive differs: ' + key)
    record.update(look_id=look, asset_id=asset, provider=provider, license='CC0-1.0', identity_notes=notes)
    record['transform_provenance'] = 'Original publisher PNGs, alignment and aspect retained. All selected normal sources are explicitly native DirectX; no green inversion or resampling baked into source maps.'
    if key == 'linen':
        record['runtime_resize_recipe'] = {'original_dimensions': [1024, 1026], 'runtime_dimensions': [1024, 1024],
                                           'originals_unchanged': True, 'height_scale': 1024 / 1026,
                                           'reason': 'Original NPOT textile requires explicit runtime import resize for mip/streaming compatibility, preserving source receipt.'}
    return key, record


def tile_mask(output, record):
    info = record['maps']['AO']
    image = source.Image.open(output / info['path'])
    if image.mode != 'L':
        raise RuntimeError('Expected source8-bit cavity AO for selected mosaic')
    value = source.np.asarray(image, dtype=source.np.float64) / 255.0
    t = source.np.clip((value - 0.90) / 0.09, 0.0, 1.0)
    smooth = t * t * (3.0 - 2.0 * t)
    # Periodic erosion conservatively keeps glaze off grout and cavity borders.
    mask = source.np.minimum.reduce([source.np.roll(smooth, (y, x), (0, 1)) for y in (-1, 0, 1) for x in (-1, 0, 1)])
    pixels = source.np.rint(mask * 255).astype(source.np.uint8)
    buffer = io.BytesIO()
    source.Image.fromarray(pixels).save(buffer, format='PNG', compress_level=9)
    record['maps']['TileMask'] = source.save_map(output, 'mosaic_clean', record['look_id'], 'TileMask', buffer.getvalue(), {
        'source_path': info['path'], 'source_sha256': info['sha256'],
        'modifications': 'Source-aligned cavity segmentation: a=AO/255; t=clamp((a-.90)/.09,0,1); s=t*t*(3-2*t); output=round(255*periodic3x3minimum(s)). No spatial hex/grid invented; one-pixel erosion conservatively excludes grout.',
        'segmentation_rationale': 'Absolute Height varies between tilted tile planes and would misclassify low tiles. Actual cavity AO is1 across tile interiors and lower along source grout, allowing stable source-aligned segmentation.',
        'usage': 'R=tile/glaze coverage;1tile0grout. Linear map, sample with exact same UVs as sourceBC/N/R.',
        'coverage_mean': float(pixels.mean() / 255), 'coverage_above_half': float((pixels >= 128).mean()),
        'max_mask_when_source_AO_at_most_0_90': int(pixels[value <= 0.90].max()),
    })


def sheet(output, materials, detail=False):
    canvas = source.Image.new('RGB', (1536, 5 * 286), (30, 30, 34))
    draw = source.ImageDraw.Draw(canvas)
    for column, key in enumerate(SELECTION):
        for row, channel in enumerate(['BaseColor', 'Normal', 'Roughness', 'Height', 'TileMask']):
            x, y = column * 256, row * 286
            draw.text((x + 4, y + 5), key + '/' + channel, fill='white')
            if channel not in materials[key]['maps']:
                draw.text((x + 4, y + 60), 'No invented mask', fill=(160, 160, 160))
                continue
            image = source.Image.open(output / materials[key]['maps'][channel]['path'])
            if image.mode in {'I', 'I;16', 'I;16B', 'I;16L'}:
                image = source.Image.fromarray(source.np.rint(source.np.asarray(image, dtype=float) / 257).astype(source.np.uint8))
            if detail:
                w, h = image.size
                image = image.crop((w // 2 - 128, h // 2 - 128, w // 2 + 128, h // 2 + 128))
            image = image.convert('RGB')
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
    licenses = []
    for provider, url in [('ambientcg', 'https://docs.ambientcg.com/license/'), ('polyhaven', 'https://polyhaven.com/license'), ('cgbookcase', CG_LICENSE_URL)]:
        path = output / 'License' / (provider + '.html')
        data = cg_cached(path, url) if provider == 'cgbookcase' else source.cached(path, url)
        if b'CC0' not in data:
            raise RuntimeError('Official license snapshot lacks CC0 statement: ' + provider)
        licenses.append({'provider': provider, 'spdx': 'CC0-1.0', 'url': url, 'path': path.relative_to(output).as_posix(), 'sha256': source.sha256(data)})
    with ThreadPoolExecutor(max_workers=3) as pool:
        materials = dict(pool.map(lambda item: source_one(item, output, pins), SELECTION.items()))
    tile_mask(output, materials['mosaic'])
    sheet(output, materials)
    sheet(output, materials, detail=True)
    helper = Path(source.__file__).resolve()
    manifest = {
        'schema_version': 1, 'retrieved_utc': pins['retrieved_utc'] if pins else datetime.now(timezone.utc).isoformat(),
        'generator_source': 'Tools/UsfMaterials/source_batch6_textures.py', 'generator_sha256': source.sha256(Path(__file__).read_bytes()),
        'required_helper': helper.relative_to(ROOT).as_posix(), 'required_helper_sha256': source.sha256(helper.read_bytes()),
        'maps_root': 'Plugins/CkTests/Resources/CkUsf/Batch6Textures', 'licenses': licenses, 'materials': materials,
        'runtime_channels': {'default': ['BaseColor', 'Normal', 'Roughness'], 'mosaic_extra': ['TileMask']}, 'runtime_texture_count': 19,
        'retained_candidates': {'Tiles019': 'Rejected visible chips/dirty aged mosaic pieces; original mosaic/Maps and archive retained. Selected clean Tiles071 uses mosaic_clean/Maps.'},
        'verification_scope': 'Official CC0 snapshots/metadata; publisher ZIP size/CRC or PolyHavenMD5; per-file SHA256 pins and truePNGdimensions/bitdepth/conventions, aligned source overview/detail and actual cavity-mask segmentation. No editor import, runtime quality, optical calibration, measured chemistry/alloy or artistic acceptance is claimed.',
        'known_download_limit': 'CGBookcase officialZIP returned403 once. Actual aligned original1K map PNGs from exact asset-page references were retrieved successfully; noZIP integrity claim is made for that asset.',
    }
    source.immutable(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({k: {'asset': r['asset_id'], 'look_id': r['look_id'], 'maps': {c: [v['width'], v['height']] for c, v in r['maps'].items()}} for k, r in materials.items()}, indent=2))
    print('Manifest SHA256', source.sha256(manifest_path.read_bytes()))


if __name__ == '__main__':
    main()
