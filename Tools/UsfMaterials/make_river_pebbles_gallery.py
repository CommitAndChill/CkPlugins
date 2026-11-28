"""Publish only verified river-pebble evidence locally; no Unreal/bridge calls.

Run only when the lead requests publication after both proofs and the fresh gate.
Earlier woodland and batch galleries are neither read as acceptance nor changed.
"""
import hashlib
import html
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'Saved/UsfMaterialGallery'
MANIFEST=ROOT/'Plugins/CkTests/Resources/CkUsf/PebbleReferenceV1/Manifest-runtime-v2.json'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition,message):
    if not condition:raise RuntimeError(message)


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def link(path):return html.escape(Path(os.path.relpath(path,OUTPUT)).as_posix(),quote=True)


def checked_image(path,expected=None):
    require(path.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n','Expected PNG: '+str(path))
    require(expected is None or digest(path)==expected,'Image changed: '+str(path))


def image_card(title,path,caption=''):
    return ('<article><h2>'+html.escape(title)+'</h2><a href="'+link(path)+'"><img loading="lazy" src="'+link(path)+'" alt="'+html.escape(title,quote=True)+'"></a><p>'+html.escape(caption)+'</p></article>')


def inputs():
    manifest=read(MANIFEST);preparation=read(OUTPUT/'RiverPebblesPreparation.json')
    proof=read(OUTPUT/'RiverPebbles-Proof.json');verification=read(OUTPUT/'RiverPebbles-Verification.json')
    orbit=read(OUTPUT/'OrbitLight-Proof.json')
    require(proof.get('passed') is True and proof.get('restored') is True and verification.get('passed') is True
            and orbit.get('passed') is True and orbit.get('restored') is True,'Both restored proofs and independent verification must pass before publication')
    require(preparation['selected_source']=='PebbleReferenceV1'
            and proof['manifest_sha256']==preparation['manifest_sha256']==verification['manifest_sha256']==digest(MANIFEST)
            and verification['proof_sha256']==digest(OUTPUT/'RiverPebbles-Proof.json')
            and verification['preparation_sha256']==digest(OUTPUT/'RiverPebblesPreparation.json')
            and verification['orbit_proof_sha256']==digest(OUTPUT/'OrbitLight-Proof.json')
            and verification['orbit_lifecycle_proof_sha256']==digest(OUTPUT/'OrbitLight-LifecycleProof.json'),'Evidence receipts changed after verification')
    shader=ROOT/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/EnvironmentRiverPebbles.ush'
    require(verification['source_shader_sha256']==digest(shader),'Selected shader changed after verification')
    for collection in ['source_file_sha256','new_asset_binary_sha256']:
        for relative,expected in verification[collection].items():
            path=(ROOT/relative).resolve();require(path.is_relative_to(ROOT.resolve()) and digest(path)==expected,'Verified source/asset changed: '+relative)
    material=manifest['materials']['pebbles'];maps=material['maps']
    require(material['look_id']=='EnvironmentRiverPebbles' and len(proof['captures'])==32,'Selected look or32-capture contract differs')
    bindings={channel+'Map':'/CkFoundation/CkUsf/Textures/Environment/'+info['runtime_name']+'.'+info['runtime_name'] for channel,info in maps.items()}
    for label,capture in proof['captures'].items():
        path=OUTPUT/capture['image']
        require(path.parent.resolve()==OUTPUT.resolve() and path.name=='RiverPebbles-'+label+'.png','Unexpected capture path')
        checked_image(path,capture['sha256'])
        require(verification['capture_sha256'].get(path.name)==digest(path)
                and all(station['textures']==bindings for station in capture['state']['environment'].values()),'Capture is stale or binds different maps')
    for channel,info in maps.items():
        path=(MANIFEST.parent/info['path']).resolve();require(path.is_relative_to(MANIFEST.parent.resolve()),'Map path escapes source owner');checked_image(path,info['sha256'])
    preview=orbit['phase_preview'];frames=preview['frames']
    require(preview['frame_count']==len(frames)==36 and preview['suggested_fps']==4
            and preview['duration_seconds']==9 and preview['playback_speed_relative_to_nominal']==2,'Declared phase-sampled preview timing differs')
    for index,frame in enumerate(frames):
        name=f'OrbitLight-Phase-{index:03d}.png';record=orbit['captures'][f'Phase-{index:03d}']
        require(frame['index']==index and frame['phase_degrees']==index*10 and frame['image']==name
                and record['image']==name and record['phase_degrees']==index*10,'Phase frame ordering differs')
        checked_image(OUTPUT/name,record['sha256'])
    settings=orbit.get('point_settings',orbit.get('expected_point_settings'))
    require(isinstance(settings,dict) and set(settings)=={'ground','ball'},'Declared Point-light settings missing')
    require(all(isinstance(value,(int,float)) and math.isfinite(value) and value>0 for group in settings.values() for value in group.values()),'Invalid declared Point-light setting')
    video=OUTPUT/'OrbitLight-Preview.mp4';require(video.is_file() and video.stat().st_size>0,'Phase-sampled video missing')
    encoding=OUTPUT/'OrbitLight-Preview.json'
    if encoding.exists():
        receipt=read(encoding)
        require(receipt['output_sha256']==digest(video) and receipt['frame_count']==36 and receipt['fps']==4
                and math.isclose(float(receipt['duration_seconds']),9,abs_tol=.05),'Video encoding receipt differs from MP4/timing')
        if 'source_frame_sha256' in receipt:
            require(receipt['source_frame_sha256']=={frame['image']:orbit['captures'][f'Phase-{i:03d}']['sha256'] for i,frame in enumerate(frames)},'Video source-frame hashes differ')
    for name in ['RiverPebbles-First.png','RiverPebbles-BC8-Native.png','ReferenceOrbit/ReferenceSheet.png']:checked_image(OUTPUT/name)
    return manifest,preparation,proof,verification,orbit,settings,shader,video


def main():
    manifest,preparation,proof,verification,orbit,settings,shader,video=inputs()
    material=manifest['materials']['pebbles'];maps=material['maps'];derivation=manifest['runtime_color_derivation']
    width,height,bar=480,330,28
    sheet=Image.new('RGB',(width*2,(height+bar)*3),'#171b22');draw=ImageDraw.Draw(sheet);cards=[]
    for row,view in enumerate(['Oblique','Low','Top']):
        for column,station in enumerate(['pom','displacement']):
            title=('POM / flat raster' if station=='pom' else 'WPO / real vertices')+' / '+view
            name=f'RiverPebbles-TAA-{station}-{view}.png';native=f'RiverPebbles-Native-{station}-{view}.png'
            with Image.open(OUTPUT/name) as source:crop=ImageOps.fit(source.convert('RGB'),(width,height),method=Image.Resampling.LANCZOS,centering=(.5,.5))
            sheet.paste(crop,(column*width,row*(height+bar)+bar));draw.text((column*width+10,row*(height+bar)+8),title,fill='#e7edf6')
            cards.append(image_card(title,OUTPUT/name,'Actual Unreal temporary TAA2 /100% capture.')[:-10]+f'<a href="{native}">Native AA0 /87% original</a></article>')
    map_cards=[image_card(channel+f' /{info["bit_depth"]}-bit '+info['color_space'],MANIFEST.parent/info['path'],'Actual selected aligned map; source-map display is separate from native shading.') for channel,info in maps.items()]
    extra=[]
    for label,capture in proof['captures'].items():
        if not label.startswith(('Native-','TAA-')):extra.append(image_card(label,OUTPUT/capture['image'],'Actual diagnostic/control/source-edit capture.'))
    controls={key:value['values'] for key,value in proof['initial_state']['environment'].items()}
    author=', '.join(material['author'])
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CkUsf river pebbles / POM, displacement and inspection light</title><style>
body{font:16px/1.5 system-ui;background:#171b22;color:#e7edf6;margin:0 auto;padding:28px;max-width:1240px}
h1{font-size:30px}h2{font-size:18px;margin:0 0 12px}a{color:#9dcbff}p{max-width:1100px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.maps{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
article,details{background:#222a35;padding:16px;border-radius:8px;margin-bottom:16px}img,video{display:block;width:100%;height:auto}
pre{overflow:auto;white-space:pre-wrap;font-size:12px}small{color:#b5c3d6}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<h1>River pebbles / POM and vertex displacement</h1>
<p>Actual Unreal captures of the selected Ganges River Pebbles scan. POM changes sampled UV appearance on a flat raster surface; WPO moves the existing256×256-cell grid vertices. Linked native views use AA0 at87%; TAA views use temporary AA2 at100%.</p>'''
    relief=preparation['height']['authored_relief_cm'];coverage=material['coverage_cm']
    page+=f'<p>Authored presentation:80×80cm, UVScale1, NormalStrength1, StepCount64 and HeightMip0. Relief is {relief:.5f}cm, guided by normal/height consistency rather than measured depth. The complete source covers about{coverage["x"]:.1f}×{coverage["y"]:.1f}cm and is deliberately presented smaller.</p>'
    page+='<p>POM does not displace raster depth, silhouettes or shadow geometry. WPO changes actual vertices; CPU collision remains unchanged. A topmost heightfield approximates rounded solid stones and cannot preserve every undercut, overhang or independent silhouette. These captures are not GPU timing or broad performance evidence.</p>'
    page+='<p><a href="RiverPebbles-ContactSheet.png">Side-by-side contact sheet</a> (identical center crops and resizing; no grading). <a href="RiverPebbles-Proof.json">32-frame controls and source-reload proof</a> · <a href="RiverPebbles-Verification.json">Independent reconciliation</a> · <a href="RiverPebblesPreparation.json">Import/grid receipt</a> · <a href="OrbitLight-Proof.json">Inspection-light proof</a></p>'
    page+='<div class="grid">'+''.join(cards)+'</div>'
    page+='<h2>Phase-sampled inspection-light preview</h2><article><video controls loop muted playsinline preload="metadata" poster="OrbitLight-Phase-000.png"><source src="OrbitLight-Preview.mp4" type="video/mp4">Open the linked MP4 to view the preview.</video>'
    page+='<p><a href="OrbitLight-Preview.mp4">MP4 original</a>. Actual paused UE captures:36 samples at10° increments, encoded at4fps for9seconds, playing at2× the nominal20°/second orbit. This is phase-sampled preview, not real-time footage or a performance measurement.</p></article>'
    if (OUTPUT/'OrbitLight-Preview.json').exists():
        page+='<p><a href="OrbitLight-Preview.json">Video encoding and timing receipt</a></p>'
    page+='<p>The reusable inspection light is a native Point light using candela units. Its declared ground/ball intensity, source radius and attenuation radius are read from the proof below. I toggles the light, P pauses/resumes it, and K resets its phase. N/B selection retargets the same inspection light to the selected material; ordinary studio rig intensities restore when it turns off.</p>'
    page+='<h2>BaseColor transfer correction / matched source-backed A/B</h2><p>The original16-bit PNG contained sRGB-encoded RGB values. ImageCore treats16/32-bit source formats as linear, so that import appeared washed out. The selected8-bit BaseColor quantizes the same encoded pixels: no gamma transform, color grading or resizing. Its texture uses sRGB decoding. Height and the other retained maps remain original16-bit source data.</p><div class="grid">'
    page+=image_card('Before / original16-bit BaseColor import',OUTPUT/'RiverPebbles-First.png','Actual native capture; retained import candidate.')
    page+=image_card('After / encodedRGB8 BaseColor import',OUTPUT/'RiverPebbles-BC8-Native.png','Actual native matched-source capture; only the BaseColor import representation changed.')+'</div>'
    page+='<h2>External target reference</h2>'+image_card('Provided reference video contact sheet',OUTPUT/'ReferenceOrbit/ReferenceSheet.png','External reference frames; not this project’s native render or evidence of a completed match.')
    page+='<h2>Licensed scan and exact source receipts</h2>'
    page+=f'<p><a href="{html.escape(material["source_url"],quote=True)}">Poly Haven / Ganges River Pebbles</a> by {html.escape(author)}, <a href="https://polyhaven.com/license">CC0</a>. Actual source maps retain their publisher bytes apart from the separately versioned encodedRGB8 BaseColor.</p>'
    original=MANIFEST.parent/'Manifest.json';recipe=ROOT/derivation['recipe_source'];original_bc=MANIFEST.parent/derivation['source_path']
    page+=f'<p><a href="{link(shader)}">Live USH source</a> · <a href="{link(original)}">Original16-bit source manifest</a> · <a href="{link(MANIFEST)}">Selected runtimeV2 manifest</a> · <a href="{link(recipe)}">BC8 derivation recipe</a> · <a href="{link(original_bc)}">Original16-bit BaseColor</a> · <a href="{link(MANIFEST.parent/maps["BaseColor"]["path"])}">Derived8-bit BaseColor</a></p>'
    page+='<div class="grid maps">'+''.join(map_cards)+'</div><details><summary>All diagnostic and source-edit captures</summary><div class="grid maps">'+''.join(extra)+'</div></details>'
    stages=''.join('<li><a href="'+html.escape(capture['image'],quote=True)+'">'+html.escape(label)+'</a></li>' for label,capture in proof['captures'].items())
    page+='<details><summary>Complete32-frame native/TAA proof index</summary><ul>'+stages+'</ul></details>'
    for title,value in [('Exact baseline controls',controls),('Declared native Point-light settings',settings),('Recomputed control/noise/recovery metrics',verification['recomputed_metrics']),('Phase-preview timing',orbit['phase_preview']),('BC8 encoded-pixel derivation',derivation),('Material instruction/sampler counts, not GPU timings',preparation['statistics'])]:
        page+='<details><summary>'+html.escape(title)+'</summary><pre>'+html.escape(json.dumps(value,indent=2))+'</pre></details>'
    page+='<small>Source fidelity, verified controls and user artistic acceptance are separate. Earlier woodland and batch evidence remains unchanged.</small></html>'
    # Write only after all evidence, source, image and movie prerequisites pass.
    sheet.save(OUTPUT/'RiverPebbles-ContactSheet.png')
    (OUTPUT/'RiverPebbles-Gallery.html').write_text(page,encoding='utf-8')
    print(OUTPUT/'RiverPebbles-Gallery.html')


if __name__=='__main__':main()
