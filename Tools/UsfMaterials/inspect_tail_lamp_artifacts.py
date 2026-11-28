"""Read-only proof/frame/source checks plus an explicit gallery inspection receipt."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'Saved/UsfMaterialGallery'


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ['src', 'href']:
                self.references.append(value)


def main():
    proof = json.loads((DIRECTORY / 'TailLamp-RenderedProof.json').read_text())
    if not proof['passed'] or not proof['restored'] or proof['cleanup_errors']:
        raise RuntimeError('Proof did not pass and restore')
    for record in proof['captures'].values():
        path = DIRECTORY / record['file']
        if path.parent != DIRECTORY or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise RuntimeError('Capture path/hash differs')
        compiled = record['state']['looks']['OpticalTailLampLens']['compiled']
        if not compiled['valid'] or compiled['closure_count'] != 1 or compiled['compile_errors']:
            raise RuntimeError('Captured shader resource was not complete')
    if any(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest for path, digest in proof['sources'].items()):
        raise RuntimeError('Restored source hash differs')
    parser = References()
    parser.feed((DIRECTORY / 'Optical-TailLamp-Gallery.html').read_text(encoding='utf-8'))
    for reference in parser.references:
        if not (DIRECTORY / reference).is_file():
            raise RuntimeError('Missing gallery reference: ' + reference)
    receipt_path = DIRECTORY / 'TailLamp-GalleryInspection.json'
    receipt = json.loads(receipt_path.read_text())
    receipt.update(unique_capture_files=len({record['file'] for record in proof['captures'].values()}),
                   local_references_checked=len(parser.references), restored_source_hashes_match=True,
                   browser_layout_verification='Blocked by browser security policy for file URLs; no workaround attempted. PNG pixels inspected directly; video full decode and local references checked.')
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
