"""Reproduce the approved sixth-look batch-seven sources without Unreal.

Retains actual publisher originals and receipts. Technical synthetic weave is
polyester-source, not verified nylon. Fiberglass is an explicitly approved,
uncalibrated derivative of an actual photographer-released glass-cloth image.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile
sys.dont_write_bytecode = True
import source_batch2_textures as source

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'Plugins/CkTests/Resources/CkUsf/Batch7Textures'
WAX_PAGE = 'https://www.texturecan.com/details/225/'
WAX_LICENSE = 'https://www.texturecan.com/terms/'
WAX_ZIP = 'https://www.texturecan.com/downloads/others_0014/others_0014_1k_2Gdj6a.zip'
GLASS_PAGE = 'https://commons.wikimedia.org/wiki/File:Glass_fabric.jpg'
GLASS_API = 'https://commons.wikimedia.org/w/api.php?action=query&titles=File:Glass_fabric.jpg&prop=imageinfo&iiprop=url%7Csize%7Cextmetadata&format=json'
GLASS_IMAGE = 'https://upload.wikimedia.org/wikipedia/commons/0/06/Glass_fabric.jpg'
SELECTION = {
    'nylon': ('LibraryNylon', 'polyhaven', 'terlenka', 'nylon', 'Technical synthetic weave: actual Terlenka POLYESTER source, not a verified nylon/polyamide scan. Nylon-style shading is independently authored; retain this source identity in labels. Original1024x1026 textile requires explicit runtime-only1024-square resize for streaming/mips.'),
    'slate': ('LibrarySlate', 'polyhaven', 'slate_floor', 'slate', 'Actual polished/coated interior slate floor with cleft stone and source seams/variation, not roof construction. No extra aging or damage added; source is not a pristine uniform geological sample.'),
    'copper': ('LibraryCopper', 'ambientcg', 'Metal057A', 'copper', 'Actual clean copper source with fine finish marks; no tarnish, oxidation or wear overlay. Conductor reflectance/finish remain authored rather than certified optical calibration.'),
    'glossy_plastic': ('LibraryGlossyPlastic', 'ambientcg', 'Plastic010', 'glossy_plastic_finish', 'Actual clean smooth plastic microfinish reused beneath independently authored glossy molded-style response. Same licensed finish identity as earlier Plastic010 uses; molding process and polymer are unverified. Reject scratched Plastic005/fingerprinted Plastic015A candidates, retained unchanged.'),
    'wax': ('LibraryWax', 'texturecan', 'others_0014', 'wax', 'Actual authored Melted Wax/Candle: red frozen drips and bumpy stacked wax, not a smooth wax slab or measured scattering scan. Native DirectX normal explicitly named in source archive.'),
    'fiberglass': ('LibraryFiberglass', 'wikimedia', 'Glass_fabric.jpg', 'fiberglass', 'Actual plain0/90 glass-fiber reinforcement cloth photograph by Cjp24, PD-self worldwide author release. Derived uncalibrated BC/N/R/relativeHeight; raw weave beneath independently authored resin response, not a cured-resin scan, calibrated reflectance or physical displacement.'),
}


def extra_cached(path, url):
    if url not in {WAX_PAGE, WAX_LICENSE, WAX_ZIP, GLASS_PAGE, GLASS_API, GLASS_IMAGE}:
        raise RuntimeError('Unexpected selected-source URL: ' + url)
    if path.exists():
        return path.read_bytes()
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'CkMaterialLibrary/1.0'}), timeout=90) as response:
        if response.url != url:
            raise RuntimeError('Unexpected source redirect: ' + response.url)
        data = response.read(32_000_001)
    if len(data) > 32_000_000:
        raise RuntimeError('Selected source exceeds focused download limit')
    source.immutable(path, data)
    return data


def png(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', compress_level=9)
    return buffer.getvalue()


def wax_source(output, look):
    page_path = output / 'Metadata/others_0014_asset.html'
    page = extra_cached(page_path, WAX_PAGE)
    if b'others_0014_1k_2Gdj6a.zip' not in page:
        raise RuntimeError('Official wax page does not identify selected archive')
    archive_path = output / 'Archives/others_0014_1k_2Gdj6a.zip'
    archive = extra_cached(archive_path, WAX_ZIP)
    record = {'source_url': WAX_PAGE, 'author': 'TextureCan (publisher; no individual author named)', 'license': 'CC0-1.0',
              'creation_method': 'Procedural / Substance Designer, official asset tags', 'coverage_cm': {'x': None, 'y': None},
              'coverage_note': 'Official page gives no calibrated coverage; no physical dimensions inferred.',
              'metadata_path': page_path.relative_to(output).as_posix(), 'metadata_sha256': source.sha256(page),
              'archive': {'path': archive_path.relative_to(output).as_posix(), 'url': WAX_ZIP, 'sha256': source.sha256(archive), 'bytes': len(archive)},
              'originals': {}, 'maps': {}}
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        if zipped.testzip() is not None:
            raise RuntimeError('Wax archive CRC failure')
        for channel, suffix, extension in [('BaseColor', 'color', 'jpg'), ('Normal', 'normal_directx', 'png'), ('Roughness', 'roughness', 'jpg'), ('Height', 'height', 'png'), ('AO', 'ao', 'jpg'), ('Subsurface', 'subsurface', 'jpg')]:
            member = f'others_0014_{suffix}_1k.{extension}'
            original = zipped.read(member)
            path = output / 'wax/Original' / member
            source.immutable(path, original)
            record['originals'][channel] = {'path': path.relative_to(output).as_posix(), 'sha256': source.sha256(original), 'archive_member': member}
            data = original if extension == 'png' else png(source.Image.open(io.BytesIO(original)).convert('RGB' if channel in {'BaseColor', 'Subsurface'} else 'L'))
            record['maps'][channel] = source.save_map(output, 'wax', look, channel, data, {
                'archive_member': member, 'source_sha256': source.sha256(original),
                'modifications': 'None; original publisher PNG bytes.' if extension == 'png' else 'Lossless PNG encoding of Pillow-decoded publisherJPEG pixels; RGB for color/subsurface, L for roughness/AO. No invented detail or resampling; untouchedJPEG retained.',
            })
    record['maps']['Subsurface']['usage'] = 'Optional retained publisher subsurface input; not measured wax scattering/thickness. Unbound in standardBCNR import.'
    return record


def glass_source(output, look):
    metadata_path = output / 'Metadata/Glass_fabric_imageinfo.json'
    metadata = extra_cached(metadata_path, GLASS_API)
    info = next(iter(json.loads(metadata)['query']['pages'].values()))['imageinfo'][0]
    rights = info['extmetadata']
    if rights['License']['value'] != 'pd' or rights['Copyrighted']['value'].lower() != 'false' or rights['LicenseShortName']['value'] != 'Public domain':
        raise RuntimeError('Original author public-domain status is not established')
    original_path = output / 'fiberglass/Original/Glass_fabric.jpg'
    original = extra_cached(original_path, GLASS_IMAGE)
    image = source.Image.open(io.BytesIO(original)).convert('RGB')
    if image.size != (1710, 923) or len(original) != info['size']:
        raise RuntimeError('Fiberglass original differs from official identity')
    # Cloth-only crop excludes the ruler, coin and cloth boundary. Mirroring
    # retains real strands while constructing a repeating texture, not new weave.
    crop = source.np.asarray(image.crop((900, 0, 1380, 480)))
    tile = source.np.concatenate((crop, crop[:, ::-1]), axis=1)
    tile = source.np.concatenate((tile, tile[::-1]), axis=0)
    tile = source.Image.fromarray(tile).resize((1024, 1024), source.Image.Resampling.LANCZOS)
    srgb = source.np.asarray(tile, dtype=source.np.float64) / 255.0
    linear = source.np.where(srgb <= .04045, srgb / 12.92, ((srgb + .055) / 1.055) ** 2.4)
    luminance = linear @ source.np.array([.2126, .7152, .0722])
    frequency = source.np.fft.fftfreq(1024)
    gaussian = source.np.exp(-2 * source.np.pi ** 2 * 24 ** 2 * (frequency[:, None] ** 2 + frequency[None, :] ** 2))
    low = source.np.fft.ifft2(source.np.fft.fft2(luminance) * gaussian).real
    detail = luminance - low
    p1, p99 = source.np.percentile(detail, [1, 99])
    height = source.np.clip(.5 + .65 * detail / (p99 - p1), 0, 1)
    base_linear = .60 + .22 * (height - .5)
    base = source.np.where(base_linear <= .0031308, base_linear * 12.92, 1.055 * base_linear ** (1 / 2.4) - .055)
    du = (source.np.roll(height, -1, 1) - source.np.roll(height, 1, 1)) * 512
    dv = (source.np.roll(height, -1, 0) - source.np.roll(height, 1, 0)) * 512
    normal = source.np.stack((-.003 * du, -.003 * dv, source.np.ones_like(height)), axis=-1)
    normal /= source.np.linalg.norm(normal, axis=-1, keepdims=True)
    images = {'BaseColor': source.Image.fromarray(source.np.repeat(source.np.rint(base * 255).astype('uint8')[:, :, None], 3, axis=2)),
              'Normal': source.Image.fromarray(source.np.rint((normal * .5 + .5) * 255).astype('uint8')),
              'Roughness': source.Image.fromarray(source.np.rint((.48 + .12 * (1 - height)) * 255).astype('uint8')),
              'Height': source.Image.fromarray(source.np.rint(height * 65535).astype('uint16'))}
    recipe = {'original_dimensions': [1710, 923], 'crop_xyxy': [900, 0, 1380, 480], 'crop_reason': 'Actual coarse550g/m2 rawglass cloth only; excludes ruler/coin/background boundary.',
              'tiling': 'Concatenate crop and X-mirror, then whole row and Y-mirror ->960square; Lanczos resize1024square. Mirrored repetition is explicit;1024output is not1024native unique photo detail.',
              'height': 'Decode sRGB to linear; Y=.2126R+.7152G+.0722B; d=Y-periodicFFTGaussian(Y,sigma24px); H=clamp(.5+.65*d/(percentile99(d)-percentile1(d)),0,1). Relative brightness surrogate, not measured geometry.',
              'detail_percentiles_1_99': [float(p1), float(p99)],
              'base_color': 'Neutral uncalibrated base: linearRGB=(.60+.22*(H-.5)).xxx; encode sRGB8. Color is authored from actual photo structure, not measured albedo.',
              'normal': 'Periodic central dH/du,dH/dv=(next-prev)*512; N=normalize(-.003*dHdu,-.003*dHdv,1); encodeRGB8. Constructed projectDirectX tangent convention, no measured normal claim.',
              'roughness': 'round(255*(.48+.12*(1-H))); authored variation surrogate, not calibrated roughness.',
              'height_mean_std': [float(height.mean()), float(height.std())], 'normal_XY_amplitude_p99': float(source.np.percentile(source.np.linalg.norm(normal[:, :, :2], axis=2), 99))}
    record = {'source_url': GLASS_PAGE, 'author': 'Cjp24;2010 ruler revision by Bewareircd (excluded from crop)', 'source_date': 'May2009; current original revision2010-09-06',
              'license': 'LicenseRef-PD-self', 'license_name': 'Worldwide public-domain release by original photographer; not relabeledCC0',
              'rights_declaration': 'I, the copyright holder of this work, release this work into the public domain. This applies worldwide. In some countries this may not be legally possible; if so: I grant anyone the right to use this work for any purpose, without any conditions, unless such conditions are required by law.',
              'metadata_path': metadata_path.relative_to(output).as_posix(), 'metadata_sha256': source.sha256(metadata),
              'originals': {'Photograph': {'path': original_path.relative_to(output).as_posix(), 'url': GLASS_IMAGE, 'sha256': source.sha256(original), 'width': 1710, 'height': 923}},
              'coverage_cm': {'x': None, 'y': None}, 'coverage_note': 'Ruler excluded from material crop; no calibrated capture geometry or physical displacement inferred.',
              'derivation_recipe': recipe, 'maps': {}}
    for channel, derived in images.items():
        record['maps'][channel] = source.save_map(output, 'fiberglass', look, channel, png(derived), {
            'source_sha256': source.sha256(original), 'modifications': 'Uncalibrated photograph-derived map; exact crop/tiling/formula in material.derivation_recipe.',
        })
    return record


def source_one(item, output, pins):
    key, (look, provider, asset, storage, notes) = item
    if provider == 'ambientcg':
        record = source.ambient_source(output, storage, look, asset, None)
    elif provider == 'polyhaven':
        record = source.poly_source(output, storage, look, asset, None)
    elif provider == 'texturecan':
        record = wax_source(output, look)
    else:
        record = glass_source(output, look)
    if not {'BaseColor', 'Normal', 'Roughness'}.issubset(record['maps']):
        raise RuntimeError('MissingBCNR: ' + key)
    for channel, entry in record['maps'].items():
        if (entry['width'], entry['height']) != ((1024, 1026) if key == 'nylon' else (1024, 1024)):
            raise RuntimeError('Unexpected source dimensions: ' + key)
        if pins and entry['sha256'] != pins['materials'][key]['maps'][channel]['sha256']:
            raise RuntimeError('Pinned source map changed: ' + key + '/' + channel)
    record.update(look_id=look, asset_id=asset, provider=provider, identity_notes=notes)
    record.setdefault('license', 'CC0-1.0')
    if key == 'nylon':
        record['runtime_resize_recipe'] = {'original_dimensions': [1024, 1026], 'runtime_dimensions': [1024, 1024], 'originals_unchanged': True, 'reason': 'Runtime-only resize for power-of-two mip/streaming compatibility; original aspect retained in receipt.'}
    return key, record


def sheet(output, materials, detail=False):
    canvas = source.Image.new('RGB', (1536, 4 * 286), (30, 30, 34))
    draw = source.ImageDraw.Draw(canvas)
    for column, key in enumerate(SELECTION):
        for row, channel in enumerate(['BaseColor', 'Normal', 'Roughness', 'Height']):
            image = source.Image.open(output / materials[key]['maps'][channel]['path'])
            if image.mode in {'I', 'I;16', 'I;16B', 'I;16L'}:
                image = source.Image.fromarray(source.np.rint(source.np.asarray(image, dtype=float) / 257).astype('uint8'))
            if detail:
                w, h = image.size
                image = image.crop((w // 2 - 128, h // 2 - 128, w // 2 + 128, h // 2 + 128))
            canvas.paste(image.convert('RGB').resize((256, 256), source.Image.Resampling.NEAREST if detail else source.Image.Resampling.LANCZOS), (column * 256, row * 286 + 25))
            draw.text((column * 256 + 4, row * 286 + 5), key + '/' + channel, fill='white')
    source.immutable(output / ('SourceDetailContactSheet.png' if detail else 'SourceMapContactSheet.png'), png(canvas))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    output = parser.parse_args().output.resolve()
    path = output / 'Manifest.json'
    pins = json.loads(path.read_text()) if path.exists() else None
    licenses = []
    for provider, url, spdx in [('ambientcg', 'https://docs.ambientcg.com/license/', 'CC0-1.0'), ('polyhaven', 'https://polyhaven.com/license', 'CC0-1.0'), ('texturecan', WAX_LICENSE, 'CC0-1.0'), ('wikimedia', GLASS_PAGE, 'LicenseRef-PD-self')]:
        receipt = output / 'License' / ('Glass_fabric_rights.html' if provider == 'wikimedia' else provider + '.html')
        data = extra_cached(receipt, url) if provider in {'texturecan', 'wikimedia'} else source.cached(receipt, url)
        if spdx == 'CC0-1.0' and b'CC0' not in data:
            raise RuntimeError('Official license is missingCC0: ' + provider)
        if provider == 'wikimedia' and b'I, the copyright holder' not in data:
            raise RuntimeError('Original author release is missing')
        licenses.append({'provider': provider, 'spdx': spdx, 'url': url, 'path': receipt.relative_to(output).as_posix(), 'sha256': source.sha256(data)})
    with ThreadPoolExecutor(max_workers=3) as pool:
        materials = dict(pool.map(lambda item: source_one(item, output, pins), SELECTION.items()))
    sheet(output, materials)
    sheet(output, materials, True)
    helper = Path(source.__file__).resolve()
    manifest = {'schema_version': 1, 'retrieved_utc': pins['retrieved_utc'] if pins else datetime.now(timezone.utc).isoformat(),
                'generator_source': 'Tools/UsfMaterials/source_batch7_textures.py', 'generator_sha256': source.sha256(Path(__file__).read_bytes()),
                'required_helper': helper.relative_to(ROOT).as_posix(), 'required_helper_sha256': source.sha256(helper.read_bytes()),
                'maps_root': 'Plugins/CkTests/Resources/CkUsf/Batch7Textures', 'licenses': licenses, 'materials': materials,
                'runtime_channels': ['BaseColor', 'Normal', 'Roughness'], 'runtime_texture_count': 18,
                'retained_candidates': {'Plastic005': 'Rejected obvious source scratches; retainedglossy_plastic/Maps/archive.', 'Plastic015A': 'Rejected visible source fingerprints; retainedglossy_plastic_clean/Maps/archive.'},
                'source_limits': 'Technical synthetic weave is polyester-source, not certified nylon. Fiberglass is an approved uncalibrated photograph derivative of raw glass cloth beneath authored resin, not a measuredPBR scan. Wax drips are actual source-authored texture relief; no silhouette displacement/SSS calibration is implied.',
                'verification_scope': 'Official rights/metadata/originals; publisherMD5 orZIPCRC; SHA256 source/derived pins, true dimensions, normal conventions and exact derivation receipts. No editor import/rendering/physical calibration/artistic acceptance claimed.'}
    source.immutable(path, (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    print('Batch7 Manifest SHA256', source.sha256(path.read_bytes()))


if __name__ == '__main__':
    main()
