"""Build the opal-polish review from actual final captures only; no studio commands."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import hashlib,html,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
def esc(value):return html.escape(str(value),quote=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class References(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.paths=set()
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in {'href','src','poster'} and value:
                parsed=urlsplit(value)
                if parsed.scheme or parsed.netloc:raise RuntimeError('Only local gallery references allowed')
                if parsed.path:self.paths.add(unquote(parsed.path))
def main():
    hashes={}
    for name in ['OpalPolish-Final.png','OpalPolish-Macro.png','OpticalDepth-Opal-Final.png','Amber-Original-IllustrativeConcept.png']:
        path=OUT/name
        if not path.is_file():raise RuntimeError('Actual capture/reference required: '+name)
        with Image.open(path) as image:
            if image.format!='PNG' or min(image.size)<600:raise RuntimeError('Full-size PNG required')
            image.load();dimensions=list(image.size)
        hashes[name]=dict(sha256=sha(path),dimensions=dimensions)
    def figure(name,caption,classes=''):
        return '<figure class="'+esc(classes)+'"><a href="'+esc(name)+'"><img loading="lazy" src="'+esc(name)+'" alt="'+esc(caption)+'"></a><figcaption>'+esc(caption)+'</figcaption></figure>'
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Opal · polished mineral study</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101216;color:#ecebee;font:16px/1.6 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:30px 28px 48px}h1{font-size:clamp(34px,4vw,48px);line-height:1.12;margin:12px 0 20px}h2{font-size:27px;margin-top:38px}p{max-width:1040px;color:#c1c3c9}a{color:#ffc786}.eyebrow{color:#d9b48a;font-size:13px;letter-spacing:.08em;text-transform:uppercase}figure{margin:18px 0;background:#080a0e;border:1px solid #30343c;border-radius:10px;overflow:hidden}figure>a{display:block}img,video{display:block;width:100%;height:auto}figcaption{padding:11px 16px;color:#c7cad0;font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.grid .actual>a{aspect-ratio:3/2;display:flex;align-items:center;justify-content:center}.grid .actual img{height:100%;object-fit:contain}.target{position:relative;aspect-ratio:3/2;overflow:hidden}.target img{position:absolute;max-width:none;width:200%;height:200%;left:-100%;top:0;object-fit:fill}details{margin:22px 0;padding:14px 18px;border:1px solid #30343c;border-radius:8px;color:#c1c3c9}summary{cursor:pointer;color:#e6d0b8}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}small{color:#a5aab5}@media(max-width:780px){main{padding:22px 16px}.grid{grid-template-columns:1fr}}
</style><main><div class="eyebrow">Actual Unreal renders · opal polish study</div><h1>Color beneath a quieter polish.</h1><p>Inspect the balance between the pale mineral body, localized colored domains and the white polished reflection. The surface highlight and buried color should read as separate visual layers.</p>'''
    encoded=OUT/'OpalPolish-EncodedMotion.json'
    if encoded.is_file():
        record=json.loads(encoded.read_text())['opal'];path=(OUT/record['file']).resolve()
        if path.parent!=OUT.resolve() or sha(path)!=record['sha256'] or not record['all_frames_decode_verified']:raise RuntimeError('Encoded motion evidence differs')
        content+='<figure><video controls loop muted playsinline preload="metadata" src="'+esc(record['file'])+'" poster="OpalPolish-Final.png"></video><figcaption>24 actual Unreal captures · changing view and illumination</figcaption></figure>'
    content+=figure('OpalPolish-Final.png','Actual Unreal render · polished opal study')+figure('OpalPolish-Macro.png','Actual Unreal macro · polished surface and mineral pattern')
    content+='<h2>Illustrative target and actual result</h2><div class="grid"><figure><div class="target"><img loading="lazy" src="Amber-Original-IllustrativeConcept.png" alt="Original illustrative opal target, upper-right concept panel"></div><figcaption>Illustrative target · not an Unreal render</figcaption></figure>'+figure('OpalPolish-Final.png','Actual Unreal render · current polish','actual')+'</div>'
    content+='<details><summary>Compare the previous opal</summary><div class="grid">'+figure('OpticalDepth-Opal-Final.png','Previous actual Unreal opal','actual')+figure('OpalPolish-Final.png','Current actual Unreal opal','actual')+'</div></details>'
    content+='<p><small>This opaque material uses two native Slabs to suggest color beneath a polished surface; it is not a spectral diffraction or volumetric transport solution. The new OpalPolishV2 maps preserve original generated color artwork unchanged and add estimated artist data, including 21 broad orientation regions with smooth transitions. They are not measured optical scans. Playback demonstrates appearance changes, not performance. User visual approval and agreement with the illustrative target remain open.</small></p>'
    links=[]
    for name,label in [('OpalPolish-Receipt.json','Capture and material record'),('OpalPolish-FreshProof.json','Material control evidence'),('OpalPolish-LiveReload.json','Live source recovery evidence')]:
        if (OUT/name).is_file():links.append('<a href="'+esc(name)+'">'+esc(label)+'</a>')
    if links:content+='<p>'+' · '.join(links)+'</p>'
    content+='<details><summary>Image hashes and dimensions</summary><pre>'+esc(json.dumps(hashes,indent=2))+'</pre></details><p><small>Browser layout inspection has not been performed.</small></p></main></html>'
    parser=References();parser.feed(content);parser.close()
    for relative in parser.paths:
        path=(OUT/relative).resolve()
        if not path.is_relative_to(OUT.resolve()) or not path.is_file():raise RuntimeError('Missing or unsafe gallery reference: '+relative)
    destination=OUT/'Opal-Polish-Gallery.html';destination.write_text(content,encoding='utf-8');print(json.dumps(dict(gallery=str(destination),local_references_verified=len(parser.paths)),indent=2))
if __name__=='__main__':main()
