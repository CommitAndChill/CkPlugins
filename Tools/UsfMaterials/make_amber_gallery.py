"""Build the amber review page only from passed, restored native Unreal evidence."""
from pathlib import Path
import hashlib
import html
from html.parser import HTMLParser
import json
import shutil
import struct
import subprocess
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'Saved/UsfMaterialGallery'
REQUIRED={'Hero','Front','Left','Right','Macro','Interior','NoInclusions','Thin','Thick','Rough','Clear','SourceEdit','SourceRecovered','HelperEdit','HelperRecovered','Final'}
REQUIRED|={'LightOrbit%02d'%i for i in range(24)}
REQUIRED|={'CameraOrbit%02d'%i for i in range(12)}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def esc(value):return html.escape(str(value),quote=True)

def motion(ffmpeg,captures,name,count,fps):
    records=[captures[name+'%02d'%i] for i in range(count)]
    signature=json.dumps(dict(frames=[r['sha256'] for r in records],fps=fps,codec='libx264',crf=18,pixels='yuv420p'),sort_keys=True)
    fingerprint=hashlib.sha256(signature.encode()).hexdigest()[:16]
    destination=OUTPUT/('Amber-'+name+'-'+fingerprint+'.mp4')
    listing=''.join("file '"+(OUTPUT/r['file']).as_posix().replace("'","'\\''")+"'\n" for r in records)
    sequence=OUTPUT/('Amber-'+name+'-'+fingerprint+'.ffconcat')
    if sequence.exists() and sequence.read_text(encoding='utf-8')!=listing:
        raise RuntimeError('Preserve differing video input: '+str(sequence))
    if not sequence.exists():sequence.write_text(listing,encoding='utf-8')
    if not destination.exists():
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-xerror','-n','-r',str(fps),'-f','concat','-safe','0','-i',str(sequence),'-frames:v',str(count),'-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(destination)],check=True)
    decoded=subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-xerror','-i',str(destination),'-map','0:v:0','-an','-progress','pipe:1','-f','null','-'],check=True,capture_output=True,text=True)
    frames=[int(line.split('=',1)[1].strip()) for line in decoded.stdout.splitlines() if line.startswith('frame=')]
    if not frames or frames[-1]!=count:raise RuntimeError('Decoded video frame count differs: '+name)
    return dict(file=destination.name,sha256=digest(destination),frames=count,fps=fps,input_sha256=[r['sha256'] for r in records],concat_file=sequence.name,concat_sha256=digest(sequence),full_decode_passed=True)

class References(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.paths=set()
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in {'href','src','poster'} and value:
                parsed=urlsplit(value)
                if parsed.scheme or parsed.netloc:raise RuntimeError('Nonlocal gallery reference: '+value)
                if parsed.path:self.paths.add(unquote(parsed.path))

def main():
    proof_path=OUTPUT/'Amber-Proof.json'
    proof=json.loads(proof_path.read_text(encoding='utf-8'))
    if proof.get('passed') is not True or proof.get('restored') is not True or proof.get('cleanup_errors')!=[]:
        raise RuntimeError('Amber proof must pass, restore, and have no cleanup errors')
    captures=proof['captures']
    if REQUIRED-set(captures):raise RuntimeError('Missing captures: '+', '.join(sorted(REQUIRED-set(captures))))
    for label,record in captures.items():
        relative=Path(record['file']);path=(OUTPUT/relative).resolve()
        if relative.is_absolute() or path.parent!=OUTPUT.resolve() or path.suffix.lower()!='.png' or digest(path)!=record['sha256']:
            raise RuntimeError('Capture path/hash differs: '+label)
        data=path.read_bytes()
        if data[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',data[16:24])!=(1600,1200):
            raise RuntimeError('Capture PNG/dimensions differ: '+label)
        compiled=record['state']['looks']['Body']['compiled']
        if not compiled['valid'] or compiled['closure_count']!=1 or compiled['compile_errors']:
            raise RuntimeError('Amber body must have one valid native closure: '+label)
    if not proof['sources']:raise RuntimeError('Current source hashes required')
    for relative,expected in proof['sources'].items():
        path=(ROOT/relative).resolve()
        if not isinstance(expected,str) or Path(relative).is_absolute() or not path.is_relative_to(ROOT.resolve()) or digest(path)!=expected:
            raise RuntimeError('Current source path/hash differs: '+relative)
    identity={key:captures['Hero']['state']['looks']['Body'][key] for key in ['master','mid','textures','front']}
    for label in ['SourceEdit','SourceRecovered','HelperEdit','HelperRecovered','Final']:
        body=captures[label]['state']['looks']['Body']
        if any(body.get(key)!=value for key,value in identity.items()):raise RuntimeError('Live-edit body identity differs: '+label)
    if captures['Interior']['state']['visible']['Body'] is not False:
        raise RuntimeError('Interior proof must hide optical cap')
    if any(captures['NoInclusions']['state']['visible'][role] is not False for role in ['Botanical','Seed','Stem']):
        raise RuntimeError('NoInclusions proof must hide actual botanical meshes')
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise RuntimeError('Existing ffmpeg executable required')
    videos={name:motion(ffmpeg,captures,name,count,fps) for name,count,fps in [('LightOrbit',24,8),('CameraOrbit',12,6)]}
    def image(label,caption):
        filename=esc(captures[label]['file'])
        return '<figure><a href="'+filename+'"><img loading="lazy" width="1600" height="1200" src="'+filename+'" alt="'+esc(caption)+'"></a><figcaption>'+esc(caption)+'</figcaption></figure>'
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CkUsf · Amber botanical specimen</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#141310;color:#eee7da;font:16px/1.6 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:48px 28px}h1{font-size:clamp(32px,4vw,56px);line-height:1.12;margin:12px 0}h2{font-size:25px;margin-top:44px}p{max-width:1050px;color:#c5bcad}.eyebrow{color:#d7ac63}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}figure{margin:0;background:#201d17;border:1px solid #40372a;border-radius:12px;overflow:hidden}img,video{width:100%;height:auto;display:block}figcaption{padding:13px 18px;color:#d7c9b3}a{color:#edc37c}.hero{margin-top:28px}.limits{border-left:3px solid #bd9149;padding-left:18px}details{margin-top:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}@media(max-width:780px){.grid{grid-template-columns:1fr}main{padding:24px 16px}}
</style><main><div class="eyebrow">CkUsf / Native amber transmission / Actual Unreal captures</div><h1>Amber.<br>Botanical depth.</h1><p>An original 11 × 8 × 2.7 cm cabochon with eight pairs of modeled fern leaflets, a twig and a separate seed wing at another depth. Authored resin flow, polishing, thickness, leaf veins and seed-fiber maps accompany the geometry. The optical material uses one native Substrate closure.</p><div class="hero">'''
    content+=image('Hero','Hero · actual native Unreal amber specimen')+'</div><h2>Inspect shape and depth</h2><div class="grid">'
    for label,caption in [('Front','Front · convex amber cap and botanical composition'),('Left','Left · interior parallax'),('Right','Right · opposite view of the same geometric inclusions'),('Macro','Macro · curved leaflets, twig and seed wing')]:content+=image(label,caption)
    content+='</div><h2>Actual interior geometry</h2><p>These visibility controls expose the separately modeled botanical meshes. Their silhouettes and depth come from geometry; the maps add surface detail.</p><div class="grid">'
    for label,caption in [('Interior','Optical cap hidden · actual botanical and seed geometry'),('NoInclusions','Botanical, stem and seed hidden · remaining optical cap and opaque backing')]:content+=image(label,caption)
    content+='</div><h2>Moving illumination and camera</h2><p>The light sequence contains 24 captured positions at 8 fps; the camera sequence contains 12 at 6 fps. Both H.264 files are decoded completely and checked for the expected frame count. These sequences demonstrate appearance and motion; they provide no performance measurement.</p><div class="grid">'
    for name,caption in [('LightOrbit','Moving light · highlight and transmission response'),('CameraOrbit','Restricted front camera sweep · geometric interior depth')]:
        content+='<figure><video controls loop muted playsinline preload="metadata" src="'+esc(videos[name]['file'])+'" poster="'+esc(captures['Final']['file'])+'"></video><figcaption>'+esc(caption)+'</figcaption></figure>'
    content+='</div><h2>Optical controls</h2><p>Optical thickness, roughness and absorption endpoints are recorded in each capture state. Reference thickness remains the material’s calibration input; authored optical thickness describes the single-sheet approximation.</p><div class="grid">'
    for label,caption in [('Thin','Thickness assay · thinner optical path'),('Thick','Thickness assay · thicker optical path'),('Rough','Surface assay · roughened amber'),('Clear','Absorption assay · clear transmission endpoint')]:content+=image(label,caption)
    content+='</div><h2>Live source edits and exact recovery</h2><p>The entrypoint and shared helper were edited and recovered in the same material instance. Master, native front node, MID and texture bindings are checked against the hero state. Current source files match the recovered proof hashes. Recorded image differences and recovery bounds are available below.</p><div class="grid">'
    for label,caption in [('SourceEdit','Live amber entrypoint edit'),('SourceRecovered','Amber entrypoint recovered'),('HelperEdit','Live shared optical helper edit'),('HelperRecovered','Shared helper recovered'),('InclusionEdit','Live shared inclusion shader edit · four opaque material consumers'),('InclusionRecovered','Shared inclusion shader recovered'),('Final','Final restored optical specimen')]:
        if label in captures:content+=image(label,caption)
    content+='</div><h2>Evidence and limits</h2><p>All linked capture hashes and 1600 × 1200 PNG dimensions are verified. Each capture reports one valid compiled native closure without compile errors. The passed proof reports restored sources and no cleanup errors. Earlier prototype assets remain outside this additive specimen’s authoring paths.</p>'
    content+='<p class="limits">This is a front-view specimen staged for approximately ±30° views: one convex exterior optical sheet over actual opaque inclusions and an opaque rear support. Material thickness does not establish a closed resin solid or entry/exit ray tracing. Native Pixel Normal Offset is screen-space refraction with foreground and offscreen limitations. No caustics or certified optical accuracy are established. Browser layout inspection is blocked by the existing local-file policy and has not been performed. Every displayed image is an actual captured render.</p>'
    content+='<details><summary>Recorded assay and recovery metrics</summary><pre>'+esc(json.dumps(proof['metrics'],indent=2))+'</pre></details>'
    content+='<p><a href="Amber-Proof.json">Amber proof and source hashes</a> · <a href="Amber-Preparation.json">Amber preparation receipt</a> · <a href="Amber-GalleryInspection.json">Gallery inspection receipt</a> · <a href="Optical-TailLamp-Refined-Gallery.html">Earlier refined tail-lamp gallery</a> · <a href="TailLamp-RefinedProof.json">Earlier refined proof</a></p></main></html>'
    references=References();references.feed(content);references.close()
    inspection_path=OUTPUT/'Amber-GalleryInspection.json'
    for relative in sorted(references.paths):
        path=(OUTPUT/relative).resolve()
        if not path.is_relative_to(OUTPUT.resolve()) or (path!=inspection_path and not path.is_file()):
            raise RuntimeError('Missing or unsafe gallery reference: '+relative)
    destination=OUTPUT/'Amber-Inclusions-Gallery.html'
    destination.write_text(content,encoding='utf-8')
    receipt=dict(proof_sha256=digest(proof_path),gallery_sha256=digest(destination),capture_count=len(captures),capture_hashes_verified=True,capture_dimensions=[1600,1200],current_source_hashes_verified=True,same_body_instance_verified=True,native_closure_count=1,passed=True,restored=True,cleanup_errors=[],metrics=proof['metrics'],videos=videos,video_full_decode_passed=True,html_local_references_verified=True,html_local_reference_count=len(references.paths),browser_layout_inspection='blocked_by_existing_local_file_policy; not performed',limitations=['Front +/-30 degree single exterior optical sheet with opaque rear support','PNO screen-space refraction, no closed solid tracing or caustics','No browser layout inspection or performance evidence'])
    inspection_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not all((OUTPUT/relative).resolve().is_file() for relative in references.paths):raise RuntimeError('Final local reference verification failed')
    print(destination)

if __name__=='__main__':main()

