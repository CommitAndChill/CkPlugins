"""Derive authored shader data from an original generated mineral color source.

Orientation, coverage and finish are artistic estimates, not measured optical maps.
"""
from pathlib import Path
import hashlib, io, json
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plugins/CkTests/Resources/CkUsf/OpticalPairV1'
SOURCE = OUT / 'Source/OpalOriginal.png'

def main():
    color = Image.open(SOURCE).convert('RGB')
    rgb = np.asarray(color, dtype=np.float32) / 255
    high, low = rgb.max(2), rgb.min(2)
    chroma = (high-low) / np.maximum(high, .001)
    mask = np.clip((chroma-.09)/.35, 0, 1)
    height = rgb.mean(2)
    smooth = np.asarray(Image.fromarray(np.uint8(height*255)).filter(ImageFilter.GaussianBlur(3)), dtype=np.float32)/255
    dy, dx = np.gradient(smooth)
    normal = np.stack((-dx*24, dy*24, np.ones_like(dx)), axis=2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    # Broad domain orientation is separate from the polished outer surface.
    coat = np.stack((-dx*.18, dy*.18, np.ones_like(dx)), axis=2)
    coat /= np.linalg.norm(coat, axis=2, keepdims=True)
    maps = {'OpalColor':color,
            'OpalDomains':Image.fromarray(np.uint8(np.clip(np.stack((mask, smooth, chroma),2),0,1)*255)),
            'OpalDomainNormal':Image.fromarray(np.uint8((normal*.5+.5)*255)),
            'OpalPolishNormal':Image.fromarray(np.uint8((coat*.5+.5)*255)),
            'OpalRoughness':Image.fromarray(np.uint8(np.clip(.22+.2*(1-mask)+.04*smooth,0,1)*255))}
    manifest = dict(schema_version=1, generator_source=Path(__file__).relative_to(ROOT).as_posix(),
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source=dict(path=SOURCE.relative_to(OUT).as_posix(),sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            provenance='Original image generation, 2026-10-21. Artistic color reference, not a scan. Utility maps are estimated artist data.'), maps={})
    pending={}
    for name, image in maps.items():
        buffer=io.BytesIO();image.save(buffer,format='PNG');data=buffer.getvalue()
        path=OUT/'Textures'/f'{name}.png'
        if path.exists() and path.read_bytes()!=data:raise RuntimeError('Preserve changed output '+str(path))
        pending[path]=data
        pixels=np.asarray(image)
        manifest['maps'][name]=dict(path=path.relative_to(OUT).as_posix(),sha256=hashlib.sha256(data).hexdigest(),
            width=image.width,height=image.height,srgb=name=='OpalColor',channels=image.mode,bit_depth=8,
            decoded_min=int(pixels.min()),decoded_max=int(pixels.max()))
    target=OUT/'OpalTextures.json';body=(json.dumps(manifest,indent=2)+'\n').encode()
    if target.exists() and target.read_bytes()!=body:raise RuntimeError('Preserve changed manifest')
    for path,data in pending.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    target.write_bytes(body)
    print(json.dumps({'maps':len(maps),'resolution':color.size,'source_sha256':manifest['source']['sha256']}))

if __name__=='__main__':main()
