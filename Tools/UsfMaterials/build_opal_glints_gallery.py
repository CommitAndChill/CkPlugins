"""Local review of hash-verified Unreal output; this never renders or edits images."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib, html, json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
def esc(value): return html.escape(str(value),quote=True)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    receipt=OUT/'OpalGlints-Receipt.json'
    if not receipt.is_file(): raise RuntimeError('Reconcile final proof before building the review')
    encoded=json.loads((OUT/'OpalGlints-EncodedMotion.json').read_text())['opal']
    if not encoded['all_frames_decode_verified'] or sha(OUT/encoded['file'])!=encoded['sha256']:
        raise RuntimeError('Motion evidence differs')
    def figure(name,caption):
        return '<figure><a href="'+esc(name)+'"><img loading="lazy" src="'+esc(name)+'" alt="'+esc(caption)+'"></a><figcaption>'+esc(caption)+'</figcaption></figure>'
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Opal · native glints</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101216;color:#ecebee;font:16px/1.6 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:30px 28px 48px}h1{font-size:clamp(34px,4vw,48px);line-height:1.12;margin:12px 0 20px}h2{font-size:27px;margin-top:38px}p{max-width:1050px;color:#c1c3c9}a{color:#ffc786}.eyebrow{color:#d9b48a;font-size:13px;letter-spacing:.08em;text-transform:uppercase}figure{margin:18px 0;background:#080a0e;border:1px solid #30343c;border-radius:10px;overflow:hidden}figure>a{display:block}img,video{display:block;width:100%;height:auto}figcaption{padding:11px 16px;color:#c7cad0;font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.target{position:relative;aspect-ratio:3/2;overflow:hidden}.target img{position:absolute;max-width:none;width:200%;height:200%;left:-100%;top:0;object-fit:fill}.compare>figure>a{aspect-ratio:3/2;display:flex;align-items:center}.compare img{height:100%;object-fit:contain}details{margin:22px 0;padding:14px 18px;border:1px solid #30343c;border-radius:8px;color:#c1c3c9}summary{cursor:pointer;color:#e6d0b8}small{color:#a5aab5}@media(max-width:780px){main{padding:22px 16px}.grid{grid-template-columns:1fr}}
</style><main><div class="eyebrow">Actual Unreal renders · native Substrate glints</div><h1>Fine sparkle beneath clear polish.</h1><p>The smooth white reflection belongs to the outer polish. Colored glints beneath it respond to the light and viewpoint. Play the short loop, then compare the native glints on and off.</p>'''
    content+='<figure><video controls loop muted playsinline preload="metadata" src="'+esc(encoded['file'])+'" poster="OpalGlints-Final.png"></video><figcaption>24 actual Unreal captures · moving light and viewpoint</figcaption></figure>'
    content+=figure('OpalGlints-Final.png','Actual Unreal render · native glints beneath the smooth outer polish')
    content+='<h2>Native glints on / off</h2><div class="grid">'+figure('OpalGlints-Final.png','Native glints enabled')+figure('OpalGlints-GlintsOff.png','Same material and lighting · glint density set to 1, the ordinary specular endpoint')+'</div>'
    content+=figure('OpalGlints-Macro.png','Actual Unreal macro · surface polish and lower mineral layer')
    content+='<h2>Illustrative target and actual result</h2><div class="grid compare"><figure><div class="target"><img loading="lazy" src="Amber-Original-IllustrativeConcept.png" alt="Original illustrative opal target"></div><figcaption>Illustrative target · not an Unreal render</figcaption></figure>'+figure('OpalGlints-Final.png','Actual Unreal render · current result')+'</div>'
    content+='<details><summary>Compare the preceding opal</summary><div class="grid">'+figure('OpalPolish-Final.png','Previous actual Unreal result')+figure('OpalGlints-Final.png','Current actual Unreal result')+'</div></details>'
    content+='<p><small>Two retained native Substrate layers, with native glints on the lower layer. Texture sampling, color, roughness, normal strength and glint density/scale are live-editable through .ush. The original color artwork and five texture maps are reused; the handmade facet study is excluded. This is an opaque artistic approximation of opal, not spectral diffraction or traced volume transport.</small></p>'
    content+='<details><summary>Implementation and verification</summary><p><a href="OpalGlints-Receipt.json">Verified capture record</a> · <a href="OpalGlints-FreshProof.json">Material controls</a> · <a href="OpalGlints-LiveReload.json">Source edit and restoration</a></p><p>Native glint feature and complex-special material path checked after compilation. Shader changes retain the same master and material instance. Default Blendable compatibility is tested separately. Browser layout has not been visually inspected.</p></details></main></html>'
    class References(HTMLParser):
        def __init__(self): super().__init__(convert_charrefs=True); self.paths=set()
        def handle_starttag(self,tag,attrs):
            for key,value in attrs:
                if key in {'href','src','poster'} and value:
                    parsed=urlsplit(value)
                    if parsed.scheme or parsed.netloc: raise RuntimeError('Only local gallery references allowed')
                    if parsed.path: self.paths.add(unquote(parsed.path))
    references=References();references.feed(content);references.close()
    for relative in references.paths:
        path=(OUT/relative).resolve()
        if not path.is_relative_to(OUT.resolve()) or not path.is_file(): raise RuntimeError('Missing/unsafe gallery reference: '+relative)
    path=OUT/'Opal-Glints-Gallery.html'
    if path.exists(): raise RuntimeError('Preserve prior review gallery')
    path.write_text(content,encoding='utf-8')
    print(json.dumps(dict(gallery=str(path),references_verified=len(references.paths)),indent=2))

if __name__=='__main__': main()
