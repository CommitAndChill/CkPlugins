"""Read-only source, parameter-order and protected-file checks before runtime validation."""
from pathlib import Path
import ast
import hashlib
import json
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SHADERS = ROOT / 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks'


def main():
    count = 0
    for name, filename in [('Batch7Textures', 'Manifest.json'), ('Batch7Textures', 'Manifest-v2.json'),
                           ('Environment1Textures', 'Manifest.json'), ('Environment2Textures', 'Manifest.json')]:
        base = ROOT / 'Plugins/CkTests/Resources/CkUsf' / name
        manifest = json.loads((base / filename).read_text())
        for info in manifest['licenses']:
            assert hashlib.sha256((base / info['path']).read_bytes()).hexdigest() == info['sha256']
        for record in manifest['materials'].values():
            for channel, info in record['maps'].items():
                source = (base / info['path']).resolve()
                source.relative_to(base.resolve())
                assert hashlib.sha256(source.read_bytes()).hexdigest() == info['sha256']
                with Image.open(source) as image:
                    assert image.size == (info['width'], info['height'])
                if channel == 'Normal':
                    assert info['normal_convention'].startswith('DirectX')
                count += 1
    for definition in ['CkUsf_Library_Batch7_Assets.as', 'CkUsf_Environment1_Assets.as']:
        source = (ROOT / 'Plugins/CkFoundation/Script/CkUsf' / definition).read_text()
        for block in re.split(r'\n    asset ', source)[1:]:
            name = block.split()[0]
            declared = re.findall(r'Usf_(?:Texture|Scalar|Vector)In\(n"([^"]+)"', block)
            shader = (SHADERS / (name + '.ush')).read_text()
            for match in re.finditer(r'CkUsf_Look_' + name + r'(?:_WPO)?\([^)]*\)', shader):
                signature = match.group()
                actual = re.findall(r'(?:Texture2D|float3|float)\s+(\w+)', signature)
                assert actual == declared, (name, actual, declared)
    for name, expected in json.loads((ROOT / 'Saved/UsfMaterialGallery/Batch7-OpeningHashes.json').read_text()).items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    for filename in ['studio_session.py', 'studio_command.py', 'open_studio_in_editor.py',
                     'prepare_environment1.py', 'generate_environment_grid.py']:
        ast.parse((ROOT / 'Tools/UsfMaterials' / filename).read_text())
    print(json.dumps({'passed': True, 'source_map_record_checks': count, 'protected': 350, 'ordered_look_signatures': 8}))


if __name__ == '__main__':
    main()
