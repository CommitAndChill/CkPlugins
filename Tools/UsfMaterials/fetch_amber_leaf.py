"""Download a public CC0 leaf set from its original provider; retain provenance."""
from pathlib import Path
import hashlib
import json
import re
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Plugins/CkTests/Resources/CkUsf/AmberHeroV1/LeafSource'
PAGE = 'https://www.cgbookcase.com/textures/thanks?r=2&t=AutumnLeaf31_MR_2K.zip&u=AutumnLeaf31'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    html = urllib.request.urlopen(urllib.request.Request(PAGE, headers={'User-Agent': 'Mozilla/5.0'})).read().decode()
    (OUTPUT / 'DownloadPage.html').write_text(html, encoding='utf-8')
    urls = re.findall(r'https[^\s"<>]+', html)
    print('\n'.join(urls))
    if '--download' not in __import__('sys').argv:
        return
    # Exact public URL construction verified in the provider's observed download script.
    url = 'https://cgbookcase-volume.b-cdn.net/t/AutumnLeaf31_MR_2K.zip'
    archive = OUTPUT / 'AutumnLeaf31_MR_2K.zip'
    if not archive.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': PAGE})
        with urllib.request.urlopen(request) as response:
            archive.write_bytes(response.read())
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            destination = (OUTPUT / item.filename).resolve()
            if not destination.is_relative_to(OUTPUT.resolve()):
                raise RuntimeError('Archive path escapes original source directory')
            if not item.is_dir():
                destination.parent.mkdir(parents=True, exist_ok=True)
                data = package.read(item)
                if destination.exists() and destination.read_bytes() != data:
                    raise RuntimeError('Preserve differing original leaf source')
                if not destination.exists():
                    destination.write_bytes(data)
    receipt = dict(provider='CGBookcase', asset='Autumn Leaf 31', page='https://www.cgbookcase.com/textures/autumn-leaf-31',
        license='CC0 1.0', license_url='https://www.cgbookcase.com/textures', download=url,
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        files={str(path.relative_to(OUTPUT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in OUTPUT.rglob('*') if path.is_file() and path.suffix.lower() in ['.png', '.jpg', '.tif', '.tiff']})
    (OUTPUT / 'Receipt.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
