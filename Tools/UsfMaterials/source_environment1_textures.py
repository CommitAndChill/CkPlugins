"""Reproduce the approved first height-backed gravel/soil source, without Unreal."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import source_batch2_textures as source

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'Plugins/CkTests/Resources/CkUsf/Environment1Textures'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    output = parser.parse_args().output.resolve()
    path = output / 'Manifest.json'
    pins = json.loads(path.read_text()) if path.exists() else None
    url = 'https://polyhaven.com/license'
    license_path = output / 'License/polyhaven.html'
    license_data = source.cached(license_path, url)
    if b'CC0' not in license_data:
        raise RuntimeError('Official license does not establish CC0')
    record = source.poly_source(output, 'gravel', 'EnvironmentGravel', 'gravelly_sand', None)
    if not {'BaseColor', 'Normal', 'Roughness', 'Height', 'AO'}.issubset(record['maps']):
        raise RuntimeError('Required real ground/height maps are missing')
    for channel, entry in record['maps'].items():
        if (entry['width'], entry['height']) != (1024, 1024):
            raise RuntimeError('Unexpected source dimensions')
        if pins and entry['sha256'] != pins['materials']['gravel']['maps'][channel]['sha256']:
            raise RuntimeError('Pinned map changed: ' + channel)
    record.update(look_id='EnvironmentGravel', asset_id='gravelly_sand', provider='polyhaven', license='CC0-1.0',
                  identity_notes='Actual gravelly sand/soil with stony coarse grain and aligned source height. No invented gravel noise, vegetation or wet-mud claim. Height is publisher-relative, not calibrated displacement in centimeters.',
                  transform_provenance='None; all original publisher1K PNG bytes, aspect and map alignment retained. Native nor_dx, no green inversion.')
    for detail in (False, True):
        canvas = source.Image.new('RGB', (1280, 286), (30, 30, 34))
        draw = source.ImageDraw.Draw(canvas)
        for i, channel in enumerate(['BaseColor', 'Normal', 'Roughness', 'Height', 'AO']):
            image = source.Image.open(output / record['maps'][channel]['path'])
            if image.mode in {'I', 'I;16', 'I;16B', 'I;16L'}:
                image = source.Image.fromarray(source.np.rint(source.np.asarray(image, dtype=float) / 257).astype(source.np.uint8))
            if detail:
                image = image.crop((384, 384, 640, 640))
            canvas.paste(image.convert('RGB').resize((256, 256), source.Image.Resampling.NEAREST if detail else source.Image.Resampling.LANCZOS), (i * 256, 25))
            draw.text((i * 256 + 4, 5), 'gravel/' + channel, fill='white')
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', compress_level=9)
        source.immutable(output / ('SourceDetailContactSheet.png' if detail else 'SourceMapContactSheet.png'), buffer.getvalue())
    helper = Path(source.__file__).resolve()
    manifest = {'schema_version': 1, 'retrieved_utc': pins['retrieved_utc'] if pins else datetime.now(timezone.utc).isoformat(),
                'generator_source': 'Tools/UsfMaterials/source_environment1_textures.py', 'generator_sha256': source.sha256(Path(__file__).read_bytes()),
                'required_helper': helper.relative_to(ROOT).as_posix(), 'required_helper_sha256': source.sha256(helper.read_bytes()),
                'maps_root': 'Plugins/CkTests/Resources/CkUsf/Environment1Textures',
                'licenses': [{'provider': 'polyhaven', 'spdx': 'CC0-1.0', 'url': url, 'path': license_path.relative_to(output).as_posix(), 'sha256': source.sha256(license_data)}],
                'materials': {'gravel': record},
                'height_contract': 'Height.r is the actual aligned publisher displacement image, linear16-bit data. Increasing values represent higher source relief; amplitude/zero plane are authored separately. POM/displacement behavior, silhouettes and grazing-angle filtering require runtime validation.',
                'verification_scope': 'Official metadata/license, publisherMD5/size, original/mapsSHA256, aligned1K dimensions and source/detail inspection. No runtime POM acceptance or physical height calibration.'}
    source.immutable(path, (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    print('Environment1 Manifest SHA256', source.sha256(path.read_bytes()))


if __name__ == '__main__':
    main()
