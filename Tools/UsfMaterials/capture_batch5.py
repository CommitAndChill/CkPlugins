"""Capture matched actual PIE views of the fifth mixed material batch."""
import json
from verify_industrial_reload import command, OUTPUT

LOOKS = ['LibraryDenim', 'LibraryConcrete', 'LibraryBrick', 'LibraryStainlessSteel', 'LibraryPlywood', 'LibraryCardboard']


def main():
    records = {}
    for preview in [False, True]:
        prefix = 'Batch5-Preview' if preview else 'Batch5'
        if preview:
            command('preview_quality')
        try:
            for name in LOOKS:
                records[prefix + '-' + name] = {}
                for view, distance, height in [('Close', 210, 35), ('Macro', 135, 20), ('Gameplay', 440, 260)]:
                    records[prefix + '-' + name][view] = command('capture', '--look', name,
                        '--name', f'{prefix}-{name}-{view}.png', '--distance', distance, '--height', height,
                        '--debug', 0, '--lighting', 'studio', '--shot')
                print('Captured ' + prefix + '-' + name, flush=True)
        finally:
            if preview:
                command('restore_quality')
    (OUTPUT / 'Batch5-LitCaptures.json').write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()

