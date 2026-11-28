"""Verify the plastic-only fill isolation and diagnostic runtime restoration."""
import json
import numpy as np
from PIL import Image
from verify_industrial_reload import command, OUTPUT


def main():
    initial = command('state')
    records = {}
    report = {'passed': False, 'restored': False, 'captures': records}
    try:
        for mode in ['On', 'Off']:
            command('plastic_fill_' + mode.lower())
            for look in ['LibraryBrass', 'LibraryTerrazzo']:
                filename = f'Batch4-FillNeighbor-{look}-{mode}.png'
                records[filename] = command('capture', '--look', look, '--shot', '--name', filename)
        command('plastic_fill_on')
        filename = 'Batch4-Fill-DiagnosticPoint.png'
        records[filename] = command('capture', '--look', 'LibraryTranslucentPlastic', '--shot', '--name', filename, '--lighting', 'point')
        command('select', '--look', 'LibraryTranslucentPlastic', '--lighting', 'studio')
        final = command('state')
        differences = {}
        for look in ['LibraryBrass', 'LibraryTerrazzo']:
            arrays = [np.asarray(Image.open(OUTPUT / f'Batch4-FillNeighbor-{look}-{mode}.png').convert('RGB'), dtype=float)[150:400,250:500]/255 for mode in ['On','Off']]
            differences[look] = float(abs(arrays[0].mean(axis=(0,1))-arrays[1].mean(axis=(0,1))).mean())
        report.update(restored=initial['library'] == final['library'] and final['diagnostic_light'] is None,
                      neighbor_mean_rgb_change=differences, final_state=final)
        report['passed'] = report['restored'] and all(v < .01 for v in differences.values())
    finally:
        command('select', '--look', 'LibraryTranslucentPlastic', '--lighting', 'studio')
        command('plastic_fill_on')
        (OUTPUT/'Batch4-FillProof.json').write_text(json.dumps(report, indent=2))
    print({k:v for k,v in report.items() if k not in ['captures','final_state']}, flush=True)
    if not report['passed']:
        raise RuntimeError('Plastic fill isolation/restoration failed')


if __name__ == '__main__':
    main()
