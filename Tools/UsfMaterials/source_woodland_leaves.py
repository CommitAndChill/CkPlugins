"""Fetch the recorded CC0 photographic leaf atlas; immutable originals only."""
from pathlib import Path
import json
import zipfile
import io
import hashlib
import source_batch2_textures as source

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'Plugins/CkTests/Resources/CkUsf/WoodlandSourcesV1'


def main():
    api_url = 'https://ambientcg.com/api/v2/full_json?id=LeafSet001&include=tagData,displayData,downloadData,dimensionsData'
    api = source.cached(DIRECTORY / 'LeafSet001-api.json', api_url)
    asset = json.loads(api)['foundAssets'][0]
    assert asset['assetId'] == 'LeafSet001'
    entry = next(item for item in asset['downloadFolders']['default']['downloadFiletypeCategories']['zip']['downloads']
                 if item['attribute'] == '1K-PNG')
    archive = source.cached(DIRECTORY / 'LeafSet001_1K-PNG.zip', entry['fullDownloadPath'])
    if len(archive) != entry['size']:
        raise RuntimeError('Official atlas archive size differs')
    maps = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        if zipped.testzip() is not None:
            raise RuntimeError('Atlas archive CRC failure')
        for name in zipped.namelist():
            if '/' not in name and name.endswith('.png'):
                data = zipped.read(name)
                source.immutable(DIRECTORY / name, data)
                maps[name] = source.sha256(data)
    license_data = source.cached(DIRECTORY / 'License.html', 'https://docs.ambientcg.com/license/')
    if b'CC0' not in license_data:
        raise RuntimeError('Official license lacks CC0')
    receipt = {'asset': 'LeafSet001', 'source_url': asset['shortLink'], 'license': 'CC0-1.0',
               'license_url': 'https://docs.ambientcg.com/license/', 'license_sha256': source.sha256(license_data),
               'archive_url': entry['fullDownloadPath'], 'archive_sha256': source.sha256(archive),
               'api_sha256': source.sha256(api), 'maps': maps,
               'notes': 'Publisher photo atlas with approximate PBR maps; no species or physical calibration inferred.'}
    source.immutable(DIRECTORY / 'Receipt.json', (json.dumps(receipt, indent=2) + '\n').encode())
    metadata_path=ROOT/'Plugins/CkTests/Resources/CkUsf/Environment1Textures/Metadata/gravelly_sand_files.json'
    descriptor=json.loads(metadata_path.read_bytes())['Diffuse']['4k']['jpg']
    soil=source.cached(DIRECTORY/'gravelly_sand_diff_4k.jpg',descriptor['url'])
    if len(soil)!=descriptor['size'] or hashlib.md5(soil).hexdigest()!=descriptor['md5']:
        raise RuntimeError('Official higher-resolution soil BC integrity differs')
    soil_receipt={'source_url':'https://polyhaven.com/a/gravelly_sand','license':'CC0-1.0',
                  'license_receipt':'Plugins/CkTests/Resources/CkUsf/Environment1Textures/Manifest.json',
                  'file':dict(descriptor,path='gravelly_sand_diff_4k.jpg',sha256=source.sha256(soil)),
                  'metadata_sha256':source.sha256(metadata_path.read_bytes()),
                  'note':'Higher-resolution same-scan BC only, registered to retained 1K height/roughness; original4K JPEG bytes.'}
    source.immutable(DIRECTORY/'Soil4KReceipt.json',(json.dumps(soil_receipt,indent=2)+'\n').encode())
    print('Leaf atlas and higher-resolution soil original bytes and licenses verified')


if __name__ == '__main__':
    main()
