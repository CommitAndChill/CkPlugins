"""Build a local gallery only after the three restored proofs and fresh gate reconcile."""
import hashlib
import html
import json
import os
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'Saved/UsfMaterialGallery'
SOURCE=ROOT/'Plugins/CkTests/Resources/CkUsf/DioramaPatchesV1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def link(path):return html.escape(Path(os.path.relpath(path,OUTPUT)).as_posix(),quote=True)


def main():
    verification=json.loads((OUTPUT/'Diorama-Verification.json').read_text())
    manifest=json.loads((SOURCE/'Manifest.json').read_text())
    preparation=json.loads((OUTPUT/'DioramaPreparation.json').read_text())
    if not verification['passed'] or verification['manifest_sha256']!=sha(SOURCE/'Manifest.json'):
        raise RuntimeError('Reconcile the selected final evidence before publication')
    if (verification['preparation_sha256']!=sha(OUTPUT/'DioramaPreparation.json')
            or verification['orbit_proof_sha256']!=sha(OUTPUT/'Diorama-OrbitProof.json')):
        raise RuntimeError('Preparation/orbit evidence changed after verification')
    for relative,expected in verification['new_asset_binary_sha256'].items():
        if sha(ROOT/relative)!=expected:raise RuntimeError('Verified asset changed: '+relative)
    for name,expected in verification['capture_sha256'].items():
        if sha(OUTPUT/name)!=expected:raise RuntimeError('Capture changed: '+name)
    for name,expected in verification['orbit_evidence']['capture_sha256'].items():
        if sha(OUTPUT/name)!=expected:raise RuntimeError('Orbit capture changed: '+name)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Grass, dirt and mud / USF material dioramas</title><style>
body{background:#161c24;color:#e5ecf5;font:16px/1.5 system-ui;max-width:1320px;margin:32px auto;padding:0 20px}
a{color:#9fd1ff}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
article,details{background:#222c38;padding:16px;border-radius:10px;margin:18px 0}img{width:100%;height:auto;display:block}
pre{white-space:pre-wrap;font-size:12px}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<h1>Grass, dirt and mud diorama patches</h1><p>Three non-repeating80cm compositions with leaves, flowers and gravel.
The views below are actual Unreal captures. Grass blades, flowers and placement are authored geometry baked into textures;
licensed scan/photo sources supply soil, leaf and mineral detail. Every look remains live-editable through .ush.</p>
<p>POM changes sampled UV appearance. Vertex displacement moves the existing dense grid; collision stays unchanged.
A topmost heightfield cannot retain independent blade silhouettes, leaf undersides or overhangs.
These are texture-backed ground materials, with no foliage geometry system or performance acceptance implied.</p>
<p>I toggles the selected-station orbit light, P pauses, K resets; N/B changes stations. Default studio lighting is used for these views.</p>
<p><a href="Diorama-Verification.json">Independent verification</a>  |  <a href="DioramaPreparation.json">Import receipt</a></p>'''
    page+='<p>Licensed detail: Poly Haven gravelly_sand by Dario Barresi, ambientCG LeafSet001 and Granite002A, CC0. Grass blades, flowers, placement and wetness are authored. Exact inputs, licenses and transformations are retained in the source manifest.</p>'
    page+='<p>Grass uses compressed1cm depth and vertex mip2 after full-height native trials produced columns. Its5.262cm source range is preserved. The WPO comparison is shallow ground cover, not a reconstruction of independent grass geometry.</p>'
    sheet=Image.new('RGB',(1200,1044),'#161c24');draw=ImageDraw.Draw(sheet)
    for row,patch in enumerate(['grass','dirt','mud']):
        record=manifest['materials'][patch];look=record['look_id'];proof=OUTPUT/('Diorama-'+patch+'-Proof.json')
        if sha(proof)!=verification['proof_sha256'][patch]:raise RuntimeError('Proof changed after verification')
        descriptions={'grass':'Arched grass clumps, small white flowers, sparse leaves and gravel.',
                      'dirt':'Open brown soil, curled photo-leaf banks, small flowers and mixed gravel.',
                      'mud':'Smooth wet basins, rough muddy rims, embedded gravel and scattered leaves.'}
        page+='<h2>'+patch.title()+'</h2><p>'+descriptions[patch]+'</p>'
        page+='<p>Source height range: '+format(record['height']['range_cm'],'.3f')+'cm; displayed relief '+format(preparation['presentation'][patch]['ReliefCm'],'.3f')+'cm. '
        page+='<a href="'+link(ROOT/('Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/'+look+'.ush'))+'">Live .ush source</a>  |  <a href="'+link(proof)+'">32-frame/four-reload proof</a></p><div class="grid">'
        for col,mode in enumerate(['pom','displacement']):
            name='Diorama-'+patch+'-TAA-'+mode+'-Oblique.png';path=OUTPUT/name
            page+='<article><h3>'+('POM' if mode=='pom' else 'Vertex displacement')+'</h3><a href="'+name+'"><img src="'+name+'" alt="'+patch+' '+mode+'"></a><p>Actual UE, temporary TAA at100%.</p></article>'
            im=Image.open(path).convert('RGB');im.thumbnail((600,320));sheet.paste(im,(col*600+(600-im.width)//2,row*348+28))
            draw.text((col*600+10,row*348+6),patch+' / '+mode,fill='white')
        page+='</div><details><summary>Other views and source maps</summary><div class="grid">'
        for mode in ['pom','displacement']:
            for view in ['Low','Top']:
                name='Diorama-'+patch+'-TAA-'+mode+'-'+view+'.png'
                page+='<article><h3>'+mode+' / '+view+'</h3><img loading="lazy" src="'+name+'" alt="'+patch+' '+view+'"></article>'
        for channel,info in record['maps'].items():
            page+='<article><h3>'+channel+'</h3><img loading="lazy" src="'+link(SOURCE/info['path'])+'" alt="'+channel+' map"></article>'
        page+='</div></details>'
        page+='<details><summary>Orbit light / opposed angles</summary><p>Actual paused UE captures, native AA0 at87%. One selected Point light; the normal rig restores when disabled. <a href="Diorama-OrbitProof.json">Light-response and restoration proof</a></p><div class="grid">'
        for phase in ['Phase0','Phase180']:
            name='Diorama-'+patch+'-Orbit-'+phase+'.png'
            page+='<article><h3>'+phase+'</h3><img loading="lazy" src="'+name+'" alt="'+patch+' orbit '+phase+'"></article>'
        page+='</div></details>'
    page+='<p><a href="'+link(SOURCE/'Manifest.json')+'">Selected source manifest and provenance</a>  |  <a href="Diorama-ContactSheet.png">Contact sheet</a></p>'
    page+='<p>Native/AA0 views, debug maps and source edits are linked in each proof. Earlier materials and galleries remain preserved. User artistic approval is separate from the technical checks.</p></html>'
    sheet.save(OUTPUT/'Diorama-ContactSheet.png');(OUTPUT/'Diorama-Gallery.html').write_text(page,encoding='utf-8')
    print(OUTPUT/'Diorama-Gallery.html')


if __name__=='__main__':main()
