"""Build an optical-pair review page from actual final Unreal captures only."""
from pathlib import Path
import hashlib,html,json
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'Saved/UsfMaterialGallery'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def esc(value):return html.escape(str(value),quote=True)

class References(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.paths=set()
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in {'href','src','poster'} and value:
                parsed=urlsplit(value)
                if parsed.scheme or parsed.netloc:raise RuntimeError('Only local gallery references allowed')
                if parsed.path:self.paths.add(unquote(parsed.path))

def main():
    captures={}
    for role in ['Opal','Display']:
        path=OUTPUT/('OpticalPair-'+role+'-Final.png')
        if not path.is_file():raise RuntimeError('Capture the actual final Unreal hero before building gallery: '+path.name)
        with Image.open(path) as image:
            if image.format!='PNG' or min(image.size)<600:raise RuntimeError('Final render must be a full-resolution PNG: '+path.name)
            image.load();size=image.size
        captures[role]=dict(file=path.name,sha256=sha(path),dimensions=list(size))
    def figure(filename,caption):
        return '<figure><a href="'+esc(filename)+'"><img loading="lazy" src="'+esc(filename)+'" alt="'+esc(caption)+'"></a><figcaption>'+esc(caption)+'</figcaption></figure>'
    def optional_control(role,suffix,caption):
        for name in ['OpticalPair-'+role+'-'+suffix+'.png',role+'-'+suffix+'.png']:
            path=OUTPUT/name
            if path.is_file():
                with Image.open(path) as image:image.load()
                return figure(name,caption)
        return ''
    def optional_motion(role):
        name='OpticalPair-'+role+'-Motion.mp4';path=OUTPUT/name
        if not path.is_file():return ''
        return '<figure class="motion"><video controls loop muted playsinline preload="metadata" src="'+esc(name)+'" poster="'+esc(captures[role]['file'])+'"></video><figcaption>Actual Unreal capture sequence · changing view or illumination. Playback is appearance evidence, not a performance measurement.</figcaption></figure>'
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Optical materials · opal and coated glass</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101216;color:#ecebee;font:16px/1.6 system-ui,sans-serif}main{max-width:1250px;margin:auto;padding:28px 24px 48px}h1{font-size:clamp(32px,4vw,46px);line-height:1.15;margin:12px 0 18px}h2{font-size:28px;line-height:1.2;margin:44px 0 12px}p{max-width:980px;color:#c1c3c9}a{color:#ffc786}.eyebrow{font-size:13px;letter-spacing:.09em;color:#d8af80;text-transform:uppercase}figure{margin:20px 0;background:#171a20;border:1px solid #30343c;border-radius:9px;overflow:hidden}img,video{display:block;width:100%;height:auto}figcaption{padding:12px 16px;color:#c7cad0;font-size:14px}.look{border-left:3px solid #d8af80;padding-left:16px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.grid figure{margin:10px 0}.notes{margin-top:40px;border-top:1px solid #30343c;padding-top:10px}small{color:#a9adb6}details{color:#c1c3c9;margin-top:18px}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:760px){main{padding:22px 16px}.grid{grid-template-columns:1fr}h2{margin-top:34px}}
</style><main><div class="eyebrow">CkUsf · Actual Unreal renders · Optical material studies</div><h1>Opal and coated glass</h1><p>Two texture-backed materials built and rendered in Unreal: a polished opal using a native two-Slab material, and a coated glass cover floating above a separate recessed instrument display. The images below are actual Unreal renders. The original concept is an illustrative reference.</p>'''
    content+='<h2>Opal: quiet milk, localized color</h2><p class="look">Look for the balance between a calm milky body and distinct colored patches, with a clean white polished highlight above them. The material should retain shape and surface polish while the colored domains provide local contrast.</p>'
    content+=figure(captures['Opal']['file'],'Actual Unreal render · native two-Slab opal with a polished outer response over colored body domains')
    opal_control=optional_control('Opal','Plain','Optional control render · plain opal endpoint for comparison with the final colored-domain material')
    content+=optional_motion('Opal')
    if opal_control:content+='<details><summary>Compare with the plain mineral endpoint</summary>'+opal_control+'</details>'
    content+='<h2>Coated glass: a clear edge, a separate display</h2><p class="look">Look at the finite polished glass edge, subtle coating color at grazing angles, and the visible gap above the recessed panel. The cyan gauge and white numerals belong to the display behind the cover; the glass carries its own reflection and coating response.</p>'
    content+=figure(captures['Display']['file'],'Actual Unreal render · coated transmitting glass above a recessed cyan instrument display and separate metal hardware')
    display_control=optional_control('Display','Clear','Optional control render · clear cover endpoint for comparison with the final coating')
    content+=optional_motion('Display')
    if display_control:content+='<details><summary>Compare with an uncoated clear cover</summary>'+display_control+'</details>'
    content+='''<section class="notes"><h2>Sources and practical limits</h2><p>The opal color source is original generated artwork. Its derived domains, normals and roughness are artist-authored estimates, not scanned or measured opal data. The instrument panel is original code-authored artwork: gauge ticks, arcs, telemetry and bars rasterized from native drawing commands. Its finish maps describe shallow manufactured surface detail. No photographic glass reflections are baked into the panel texture.</p><p>The opal combines native BRDF response with an artist model of structural color. It is a finite visual approximation, not a spectral scattering solver. The glass uses neutral Pixel Normal Offset refraction; it does not establish traced entry and exit interfaces through the complete solid. These renders do not establish caustics, measured optical accuracy or performance results.</p>'''
    links=[]
    for filename,label in [('OpticalPair-Preparation.json','Asset preparation and source hashes'),('OpticalPair-Receipt.json','Capture and material receipt'),('OpticalPair-RenderedReceipt.json','Rendered capture receipt'),('OpticalPair-Proof.json','Rendered material proof'),('Amber-Polish-Gallery.html','Previously accepted amber')]:
        if (OUTPUT/filename).is_file():links.append('<a href="'+esc(filename)+'">'+esc(label)+'</a>')
    if links:content+='<p>'+' · '.join(links)+'</p>'
    content+='<details><summary>Final image hashes and dimensions</summary><pre>'+esc(json.dumps(captures,indent=2))+'</pre></details><p><small>Browser layout inspection has not been performed. Optional motion files and control images appear only when present alongside the final captures.</small></p></section></main></html>'
    references=References();references.feed(content);references.close()
    for relative in references.paths:
        path=(OUTPUT/relative).resolve()
        if not path.is_relative_to(OUTPUT.resolve()) or not path.is_file():raise RuntimeError('Missing or unsafe local gallery reference: '+relative)
    destination=OUTPUT/'Optical-Pair-Gallery.html';destination.write_text(content,encoding='utf-8')
    print(json.dumps(dict(gallery=str(destination),captures=captures,local_references_verified=len(references.paths)),indent=2))
if __name__=='__main__':main()
