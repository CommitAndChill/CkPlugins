"""Capture the six real PIE specimens through the input-independent bridge."""
import argparse
import json
from verify_industrial_reload import command, OUTPUT

LOOKS = ['LibrarySilk', 'LibraryLeather', 'LibraryTile', 'LibraryOak', 'LibraryAluminum', 'LibraryPlastic']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Temporary TAA/100% preview; restore renderer cvars afterward')
    args = parser.parse_args()
    records = {}
    prefix = 'Batch1-Preview' if args.preview else 'Batch1'
    if args.preview:
        command('preview_quality')
    try:
        for name in LOOKS:
            records[name] = {}
            for view, distance, height in [('Close', 210, 35), ('Gameplay', 440, 260), ('Macro', 135, 20)]:
                filename = f'{prefix}-{name}-{view}.png'
                extra = ['--shot'] if args.preview else []
                result = command('capture', '--look', name, '--name', filename, '--distance', distance, '--height', height,
                                 '--debug', 0, '--lighting', 'studio', *extra)
                records[name][view] = result
            print('Captured ' + name, flush=True)
        (OUTPUT / (prefix + '-LitCaptures.json')).write_text(json.dumps(records, indent=2))
    finally:
        if args.preview:
            command('restore_quality')


if __name__ == '__main__':
    main()
