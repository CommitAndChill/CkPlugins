"""Build a new depth-study gallery only after its actual final Unreal frames exist."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import hashlib,html,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'Saved/UsfMaterialGallery'
def esc(value):return html.escape(str(value),quote=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class References(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.paths=set()
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in {'href','src','poster'} and value:
                parsed=urlsplit(value)
                if parsed.scheme or parsed.netloc:raise RuntimeError('Unexpected nonlocal depth-gallery reference')
                if parsed.path:self.paths.add(unquote(parsed.path))
def main():
    evidence={}
    def png(filename,required=False):
        path=OUTPUT/filename
        if not path.is_file():
            if required:raise RuntimeError('Capture final native Unreal render first: '+filename)
            return None
        with Image.open(path) as image:
            if image.format!='PNG' or min(image.size)<600:raise RuntimeError('Full-resolution PNG required: '+filename)
            image.load();size=list(image.size)
        evidence[filename]=dict(sha256=sha(path),dimensions=size);return filename
    display=png('OpticalDepth-Display-Final.png',True);opal=png('OpticalDepth-Opal-Final.png',True)
    concept=png('Amber-Original-IllustrativeConcept.png',True)
    old_display=png('OpticalPair-Display-Final.png');old_opal=png('OpticalPair-Opal-Final.png')
    macro=png('OpticalDepth-Display-Macro.png') or png('OpticalDepth-Macro.png')
    controls=[]
    for filename,caption in [('OpticalDepth-Display-Uncoated.png','Coating disabled; subtle difference'),('OpticalDepth-Display-CoverOff.png','Glass cover hidden'),('OpticalDepth-Opal-FlashOff.png','Colored mineral response disabled'),('OpticalDepth-Opal-DepthOff.png','Buried UV depth and second sample disabled')]:
        if png(filename):controls.append((filename,caption))
    def figure(filename,caption,classes=''):
        return '<figure class="'+esc(classes)+'"><a href="'+esc(filename)+'"><img loading="lazy" src="'+esc(filename)+'" alt="'+esc(caption)+'"></a><figcaption>'+esc(caption)+'</figcaption></figure>'
    def target(quadrant,caption):
        return '<figure><div class="target '+quadrant+'"><img loading="lazy" src="'+esc(concept)+'" alt="'+esc(caption)+'"></div><figcaption>'+esc(caption)+'</figcaption></figure>'
    def motion(role,poster):
        name='OpticalDepth-'+role+'-Motion.mp4'
        if not (OUTPUT/name).is_file():return ''
        return '<figure><video controls loop muted playsinline preload="metadata" src="'+esc(name)+'" poster="'+esc(poster)+'"></video><figcaption>Actual Unreal capture sequence · inspect the changing edge and surface response</figcaption></figure>'
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Optical depth · glass and opal</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101216;color:#ecebee;font:16px/1.6 system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:30px 28px 50px}h1{font-size:clamp(34px,4vw,48px);line-height:1.12;margin:12px 0 20px}h2{font-size:28px;line-height:1.2;margin:42px 0 12px}p{max-width:1050px;color:#c1c3c9}a{color:#ffc786}.eyebrow{color:#d9b48a;font-size:13px;letter-spacing:.08em;text-transform:uppercase}figure{margin:18px 0;background:#080a0e;border:1px solid #30343c;border-radius:10px;overflow:hidden}figure>a{display:block}figure img,video{display:block;width:100%;height:auto}figcaption{padding:11px 16px;font-size:14px;color:#c7cad0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.grid figure{margin:10px 0}.grid .actual>a{aspect-ratio:3/2;display:flex;align-items:center;justify-content:center;background:#080a0e}.grid .actual img{height:100%;object-fit:contain}.target{position:relative;aspect-ratio:3/2;overflow:hidden}.target img{position:absolute;max-width:none;width:200%;height:200%;object-fit:fill;left:-100%}.target.glass img{top:-100%}.target.opal img{top:0}.inspect{border-left:3px solid #d9b48a;padding-left:16px}details{margin:22px 0;padding:14px 18px;border:1px solid #30343c;border-radius:8px;color:#c1c3c9}summary{cursor:pointer;color:#e6d0b8}small{color:#a5aab5}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:780px){main{padding:22px 16px}.grid{grid-template-columns:1fr}}
</style><main><div class="eyebrow">Actual Unreal renders · new optical depth study</div><h1>A deeper glass edge.<br>A polished opal surface.</h1><p>The new glass cover has an 18 mm transparent section above a recessed instrument display. The earlier cover was 3.3 mm thick. The illustrative target is shown separately for direct visual comparison.</p>'''
    content+=motion('Display',display)
    content+=figure(display,'Actual Unreal render · 18 mm cover, crisp chamfers and recessed illuminated display')
    content+='<p class="inspect">The cover is real geometry: an 18 mm section with 1.5 mm chamfers and an 8.9 mm gap above the panel. A stronger blue-green edge response helps reveal its thickness. The current glass does not yet match the concept’s internal refraction; the comparison below keeps that gap visible.</p>'
    if macro:content+=figure(macro,'Actual Unreal macro · transparent side wall, bevels and panel separation')
    content+='<h2>Glass: target and actual result</h2><div class="grid">'+target('glass','Illustrative target · original concept, lower-right panel')+figure(display,'Actual Unreal render · current glass and display','actual')+'</div>'
    if old_display:content+='<details><summary>Compare the earlier 3.3 mm cover</summary><div class="grid">'+figure(old_display,'Earlier actual Unreal render · 3.3 mm cover','actual')+figure(display,'New actual Unreal render · 18 mm cover','actual')+'</div></details>'
    content+='<h2>Opal: color beneath the polish</h2><p class="inspect">Look for colored patterns that appear buried beneath the polished surface, shifting below the white highlight while the body retains a quiet milky character.</p>'
    content+=motion('Opal',opal)+figure(opal,'Actual Unreal render · opal pattern beneath a polished outer response')
    content+='<details><summary>Compare the opal with the illustrative target</summary><div class="grid">'+target('opal','Illustrative target · original concept, upper-right panel')+figure(opal,'Actual Unreal render · current opal','actual')+'</div></details>'
    if old_opal:content+='<details><summary>Earlier opal presentation</summary><div class="grid">'+figure(old_opal,'Earlier actual Unreal opal render','actual')+figure(opal,'Current actual Unreal opal render','actual')+'</div></details>'
    if controls:
        content+='<details><summary>Plain material controls</summary><div class="grid">'
        for filename,caption in controls:content+=figure(filename,'Actual Unreal render · '+caption,'actual')
        content+='</div></details>'
    content+='''<details><summary>Material notes and limits</summary><p>The opal uses native material response and original artist texture data to suggest buried structural color. Its opaque volume is an appearance approximation; it does not establish a spectral or volumetric transport solution. The glass uses neutral Pixel Normal Offset. Its real mesh thickness and bevels establish visible geometry, but refraction is not traced through entry and exit interfaces. The instrument graphics are original code-authored artwork. The reference panels are illustrative concepts, not engine renders.</p><p>Capture sequences show appearance changes; they do not provide performance evidence. Browser layout inspection has not been performed.</p></details>'''
    receipt=OUTPUT/'OpticalDepth-Receipt.json'
    if receipt.is_file():content+='<p><a href="OpticalDepth-Receipt.json">Capture and material record</a></p>'
    content+='<details><summary>Image dimensions and hashes</summary><pre>'+esc(json.dumps(evidence,indent=2))+'</pre></details></main></html>'
    parser=References();parser.feed(content);parser.close()
    for relative in parser.paths:
        path=(OUTPUT/relative).resolve()
        if not path.is_relative_to(OUTPUT.resolve()) or not path.is_file():raise RuntimeError('Missing/unsafe local depth-gallery reference: '+relative)
    destination=OUTPUT/'Optical-Depth-Gallery.html';destination.write_text(content,encoding='utf-8')
    print(json.dumps(dict(gallery=str(destination),local_references_verified=len(parser.paths),images=evidence),indent=2))
if __name__=='__main__':main()
