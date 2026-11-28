"""Reproduce the approved coarser gravel-floor source without replacing Environment1."""
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
DEFAULT = ROOT / 'Plugins/CkTests/Resources/CkUsf/Environment2Textures'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    output = parser.parse_args().output.resolve()
    path = output / 'Manifest.json'
    pins = json.loads(path.read_text()) if path.exists() else None
    license_path = output / 'License/polyhaven.html'
    url = 'https://polyhaven.com/license'
    license_data = source.cached(license_path, url)
    if b'CC0' not in license_data:
        raise RuntimeError('Official license does not establishCC0')
    record = source.poly_source(output, 'gravel', 'EnvironmentGravel', 'gravel_floor', None)
    if not {'BaseColor', 'Normal', 'Roughness', 'Height', 'AO'}.issubset(record['maps']):
        raise RuntimeError('Required aligned source height/AO/BCNR are missing')
    for channel, entry in record['maps'].items():
        if (entry['width'], entry['height']) != (1024, 1024):
            raise RuntimeError('Unexpected source dimensions')
        entry['runtime_name'] = 'T_EnvironmentGravelV2_' + channel
        if pins and entry['sha256'] != pins['materials']['gravel']['maps'][channel]['sha256']:
            raise RuntimeError('Pinned source differs: ' + channel)
    record.update(look_id='EnvironmentGravel', asset_id='gravel_floor', provider='polyhaven', license='CC0-1.0',
                  identity_notes='Actual coarse pebbly gravel floor/driveway source with rough uneven warm stones. Replaces the finer gravelly_sand candidate in the existing EnvironmentGravel showcase only; no newlook/actor contract. No added vegetation, generic noise, wet mud or calibrated centimeter displacement claim.',
                  transform_provenance='None; original publisher1K PNG bytes, map alignment and aspect retained. NativeDirectX nor_dx, no green inversion.')
    for detail in (False, True):
        canvas = source.Image.new('RGB', (1280, 286), (30, 30, 34))
        draw = source.ImageDraw.Draw(canvas)
        for i, channel in enumerate(['BaseColor', 'Normal', 'Roughness', 'Height', 'AO']):
            image = source.Image.open(output / record['maps'][channel]['path'])
            if image.mode in {'I', 'I;16', 'I;16B', 'I;16L'}:
                image = source.Image.fromarray(source.np.rint(source.np.asarray(image, dtype=float) / 257).astype('uint8'))
            if detail:
                image = image.crop((384, 384, 640, 640))
            canvas.paste(image.convert('RGB').resize((256, 256), source.Image.Resampling.NEAREST if detail else source.Image.Resampling.LANCZOS), (i * 256, 25))
            draw.text((i * 256 + 4, 5), 'gravel_floor/' + channel, fill='white')
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', compress_level=9)
        source.immutable(output / ('SourceDetailContactSheet.png' if detail else 'SourceMapContactSheet.png'), buffer.getvalue())
    helper = Path(source.__file__).resolve()
    manifest = {'schema_version': 1, 'retrieved_utc': pins['retrieved_utc'] if pins else datetime.now(timezone.utc).isoformat(),
                'generator_source': 'Tools/UsfMaterials/source_environment2_textures.py', 'generator_sha256': source.sha256(Path(__file__).read_bytes()),
                'required_helper': helper.relative_to(ROOT).as_posix(), 'required_helper_sha256': source.sha256(helper.read_bytes()),
                'maps_root': 'Plugins/CkTests/Resources/CkUsf/Environment2Textures',
                'licenses': [{'provider': 'polyhaven', 'spdx': 'CC0-1.0', 'url': url, 'path': license_path.relative_to(output).as_posix(), 'sha256': source.sha256(license_data)}],
                'materials': {'gravel': record}, 'runtime_texture_count': 5,
                'version_contract': 'Retain allEnvironment1 source/assets as candidate. Existing look/master EnvironmentGravel consumes separately importedT_EnvironmentGravelV2_* textures; no new station actors/master.',
                'height_contract': 'Height.r is aligned publisher-relative linear16bit displacement; increasing values mean higher source relief. Runtime amplitude/zero plane are authored separately. Source data does not establish rendered POM/displacement behavior, silhouettes or calibrated centimeters.',
                'verification_scope': 'OfficialCC0/metadata, publisherMD5/size, sourceSHA256, aligned1K dimensions and actual source/detail inspection. Runtime acceptance remains separate.'}
    source.immutable(path, (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    print('Environment2 Manifest SHA256', source.sha256(path.read_bytes()))


if __name__ == '__main__':
    main()
