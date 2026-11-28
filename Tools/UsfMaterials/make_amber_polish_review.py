"""Publish actual matched captures as a local before/after review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/UsfMaterialGallery'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = OUT / 'AmberHero-Fidelity-Final.png'
    after = OUT / 'AmberPolish-Final.png'
    if sha(before) != 'ed79b6829be05b41e4a510ca1d7feec6d0c0e697feb7f6c83218a8dbc95694a0':
        raise RuntimeError('Accepted capture changed; preserve it')
    state = json.loads((OUT / 'AmberPolish-FinalState.json').read_text())['state']
    probes = json.loads((OUT / 'AmberPolish-Probes.json').read_text())
    for record in probes.values():
        if sha(OUT / record['file']) != record['sha256']:
            raise RuntimeError('Probe capture changed')
    body = state['looks']['Body']
    if not body['compiled']['valid'] or body['compiled']['compile_errors']:
        raise RuntimeError('Final native body resource is not ready')
    page = OUT / 'Amber-Polish-Gallery.html'
    page.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Amber · subtle polish</title><style>
body{margin:0;background:#101216;color:#ecebee;font:16px/1.6 system-ui}main{max-width:1250px;margin:auto;padding:28px 24px}h1{font-size:38px;line-height:1.15}p{max-width:900px;color:#c1c3c9}a{color:#ffc786}.compare{position:relative;aspect-ratio:4/3;overflow:hidden;background:#000}.compare img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}#before{clip-path:inset(0 50% 0 0)}#divider{position:absolute;left:50%;height:100%;width:2px;background:#ffd296}.tag{position:absolute;top:15px;padding:4px 10px;background:#111b;border-radius:4px}.left{left:15px}.right{right:15px}input{width:100%;accent-color:#e4ac67}label{display:block;margin:16px 0}small{color:#a9adb6}</style>
<main><h1>Amber: a quieter, softer presentation</h1>
<p>The accepted amber, refined with a softer rear light, a less luminous leaf and brown sediment without the distracting floor specks. The camera, amber color, texture sources and inclusion arrangement are retained.</p>
<div class="compare"><img src="AmberPolish-Final.png" alt="Polished amber"><img id="before" src="AmberHero-Fidelity-Final.png" alt="Previously accepted amber"><div id="divider"></div><span class="tag left">Accepted version</span><span class="tag right">Polished version</span></div>
<label for="split">Drag to compare the actual Unreal renders<input id="split" type="range" min="0" max="100" value="50"></label>
<p><a href="AmberPolish-Final.png">Full polished image</a> · <a href="AmberHero-Fidelity-Final.png">Accepted image</a> · <a href="AmberPolish-Receipt.json">Capture and source record</a></p>
<small>Texture-backed and live-editable through CkUsf .ush parameters. This is the working PNO optical material; the previously reported strong-refraction limitation remains. The lower-camera experiment was rejected after visual comparison.</small>
<script>const s=document.getElementById('split');s.addEventListener('input',()=>{document.getElementById('before').style.clipPath=`inset(0 ${100-s.value}% 0 0)`;document.getElementById('divider').style.left=s.value+'%';});</script></main></html>''', encoding='utf-8')
    paths = ['Tools/UsfMaterials/amber_hero_scene.py', 'Tools/UsfMaterials/amber_specimen_session.py',
             'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/AmberHeroLeaf.ush',
             'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/AmberSpecimen.ush']
    receipt = dict(status='polish_ready_for_visual_review', accepted_capture_preserved=True,
        before_sha256=sha(before), after_sha256=sha(after), page_sha256=sha(page),
        selected=probes['LeafQuiet']['request'], state=state,
        source_sha256={p:sha(ROOT/p) for p in paths},
        evidence='Six matched variants, actual final capture, same Body master/MID, valid shader resource',
        limits=['Visual polish only; no new optical capability', 'No performance claim', 'Browser layout not verified'])
    (OUT/'AmberPolish-Receipt.json').write_text(json.dumps(receipt, indent=2))
    print(page)


if __name__ == '__main__':
    main()
