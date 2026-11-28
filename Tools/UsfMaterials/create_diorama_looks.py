"""Create three new .ush/asset definitions from the verified height-material contract."""
import hashlib
import json
from pathlib import Path
from diorama_settings import presentation

ROOT=Path(__file__).resolve().parents[2]
FOUNDATION=ROOT/'Plugins/CkFoundation'


def main():
    manifest=json.loads((ROOT/'Plugins/CkTests/Resources/CkUsf/DioramaPatchesV1/Manifest.json').read_text())
    previous=json.loads((ROOT/'Saved/UsfMaterialGallery/RiverPebbles-Verification.json').read_text())
    shader=FOUNDATION/'Source/CkUsf/Shaders/CkUsf/Looks/EnvironmentRiverPebbles.ush'
    if hashlib.sha256(shader.read_bytes()).hexdigest()!=previous['source_shader_sha256']:
        raise RuntimeError('Verified template changed; inspect before authoring new looks')
    definition=(FOUNDATION/'Script/CkUsf/CkUsf_RiverPebbles_Assets.as').read_text()
    targets={}
    for key,record in manifest['materials'].items():
        look=record['look_id']
        text=shader.read_text().replace('EnvironmentRiverPebbles',look).replace('CkUsf_RiverPebblePom','CkUsf_Diorama'+key.title()+'Pom')
        text=text.replace('Dense scan-backed river pebbles','Authored texture-backed '+key+' diorama')
        text=text.replace('The sourced normal and relative height describe the same scan.',
                          'The baked normal and height describe the same authored topmost surface.')
        text=text.replace('It already contains the broad stone slopes; adding them again doubles the response.',
                          'Do not add the height slope again to the already complete normal bake.')
        # Repeated UV ramps make shallow relief measurable without amplifying display noise.
        text=text.replace('saturate(DiagnosticUV * 0.9 + 0.05)','frac(DiagnosticUV * 4.0)')
        asset=definition.replace('EnvironmentRiverPebblesBC8_BaseColor',look+'_BaseColor').replace('EnvironmentRiverPebbles',look)
        settings=presentation(record)
        asset=asset.replace('5.48848',format(settings['ReliefCm'],'.12g'))
        asset=asset.replace('n"HeightMip", 0,', 'n"HeightMip", '+str(settings['HeightMip'])+',')
        targets[FOUNDATION/('Source/CkUsf/Shaders/CkUsf/Looks/'+look+'.ush')]=text
        targets[FOUNDATION/('Script/CkUsf/CkUsf_Diorama'+key.title()+'_Assets.as')]=asset
    for path,text in targets.items():
        if path.exists() and path.read_text()!=text:
            raise RuntimeError('Existing new-look source differs; preserve it: '+str(path))
    for path,text in targets.items():
        if not path.exists():path.write_bytes(text.replace('\r\n','\n').replace('\n','\r\n').encode())
        print(path.relative_to(ROOT))


if __name__=='__main__':main()
