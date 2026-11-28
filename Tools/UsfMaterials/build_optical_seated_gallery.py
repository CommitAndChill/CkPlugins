"""Build the seated-glass review page only after the lead authorizes completed captures."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import hashlib,html,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'Saved/UsfMaterialGallery'
def esc(value):return html.escape(str(value),quote=True)
class References(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.paths=set()
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in {'href','src','poster'} and value:
                parsed=urlsplit(value)
                if parsed.scheme or parsed.netloc:raise RuntimeError('Only local seated-gallery references are permitted')
                if parsed.path:self.paths.add(unquote(parsed.path))
def main():
    images={}
    def png(filename):
        path=OUTPUT/filename
        if not path.is_file():raise RuntimeError('Capture must exist before gallery generation: '+filename)
        with Image.open(path) as image:
            if image.format!='PNG' or min(image.size)<600:raise RuntimeError('Full-resolution PNG capture required: '+filename)
            image.load();dimensions=list(image.size)
        images[filename]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),dimensions=dimensions)
        return filename
    final=png('OpticalSeated-Display-Final.png');macro=png('OpticalSeated-Display-Macro.png')
    previous=png('OpticalDepth-Display-Final.png');concept=png('Amber-Original-IllustrativeConcept.png')
    def figure(filename,caption,classes=''):
        return '<figure class="'+esc(classes)+'"><a href="'+esc(filename)+'"><img loading="lazy" src="'+esc(filename)+'" alt="'+esc(caption)+'"></a><figcaption>'+esc(caption)+'</figcaption></figure>'
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Seated glass · machined aluminum</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101216;color:#ecebee;font:16px/1.6 system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:30px 28px 48px}h1{font-size:clamp(34px,4vw,48px);line-height:1.12;margin:12px 0 20px}h2{font-size:27px;margin:38px 0 12px}p{max-width:1020px;color:#c1c3c9}a{color:#ffc786}.eyebrow{color:#d9b48a;font-size:13px;letter-spacing:.08em;text-transform:uppercase}figure{margin:18px 0;background:#080a0e;border:1px solid #30343c;border-radius:10px;overflow:hidden}figure>a{display:block}figure img,video{display:block;width:100%;height:auto}figcaption{padding:11px 16px;font-size:14px;color:#c7cad0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.grid figure{margin:10px 0}.grid .actual>a{aspect-ratio:3/2;display:flex;align-items:center;justify-content:center}.grid .actual img{height:100%;object-fit:contain}.target{position:relative;aspect-ratio:3/2;overflow:hidden}.target img{position:absolute;max-width:none;width:200%;height:200%;left:-100%;top:-100%;object-fit:fill}.inspect{border-left:3px solid #d9b48a;padding-left:16px}details{margin:22px 0;padding:14px 18px;border:1px solid #30343c;border-radius:8px;color:#c1c3c9}summary{cursor:pointer;color:#e6d0b8}small{color:#a5aab5}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:780px){main{padding:22px 16px}.grid{grid-template-columns:1fr}}
</style><main><div class="eyebrow">Actual Unreal renders · seated display refinement</div><h1>Seated glass.<br>Machined aluminum.</h1><p>Inspect the glass resting on a continuous perimeter rim with a 0.2 mm fit seam and no support posts. Broad, flat machined shoulders meet small 45-degree chamfers; the rounded outer corners are retained.</p>'''
    movie='OpticalSeated-Display-Orbit.mp4'
    if (OUTPUT/movie).is_file():
        content+='<figure><video controls loop muted playsinline preload="metadata" src="'+esc(movie)+'" poster="'+esc(final)+'"></video><figcaption>Actual Unreal orbit captures · inspect changing bevel color and the continuous seat</figcaption></figure>'
    content+=figure(final,'Actual Unreal render · seated glass, continuous rim and machined aluminum housing')
    content+='<p class="inspect">Look for the fitted glass-to-rim seam, flat aluminum shoulders and crisp chamfers. The bevels carry the strongest colored film response, with a quieter sidewall finish. The instrument graphic remains behind the cover.</p>'
    content+=figure(macro,'Actual Unreal macro · glass bevel, continuous seat and small aluminum chamfers')
    content+='<h2>Illustrative target and actual result</h2><div class="grid"><figure><div class="target"><img loading="lazy" src="'+esc(concept)+'" alt="Original illustrative coated-glass target, lower-right concept panel"></div><figcaption>Illustrative target · original concept, not an Unreal render</figcaption></figure>'+figure(final,'Actual Unreal render · current seated assembly','actual')+'</div>'
    content+='<details><summary>Compare the previous depth study</summary><div class="grid">'+figure(previous,'Previous actual Unreal render · separated cover and supports','actual')+figure(final,'Current actual Unreal render · continuous perimeter seat','actual')+'</div></details>'
    content+='<p><small>The rainbow is RGB thin-film interference reflectance: full strength on the bevels and 20% on the sidewalls. It is not true wavelength-dependent refraction. Native neutral Pixel Normal Offset does not physically trace background bending or internal reflections. Final visual approval and full agreement with the illustrative target remain open.</small></p><details><summary>Review notes</summary><p>Orbit playback demonstrates appearance changes, not performance. Browser layout inspection has not been performed.</p></details>'
    if (OUTPUT/'OpticalSeated-Receipt.json').is_file():content+='<p><a href="OpticalSeated-Receipt.json">Capture and material record</a></p>'
    content+='<details><summary>Image hashes and dimensions</summary><pre>'+esc(json.dumps(images,indent=2))+'</pre></details></main></html>'
    references=References();references.feed(content);references.close()
    for relative in references.paths:
        path=(OUTPUT/relative).resolve()
        if not path.is_relative_to(OUTPUT.resolve()) or not path.is_file():raise RuntimeError('Missing or unsafe local seated-gallery reference: '+relative)
    destination=OUTPUT/'Optical-Seated-Gallery.html';destination.write_text(content,encoding='utf-8')
    print(json.dumps(dict(gallery=str(destination),local_references_verified=len(references.paths),images=images),indent=2))
if __name__=='__main__':main()

