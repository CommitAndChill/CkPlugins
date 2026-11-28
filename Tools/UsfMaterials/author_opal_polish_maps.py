"""Author numerical opal maps from an unchanged original RGB artwork; no appearance editing."""
from pathlib import Path
from collections import deque
import argparse,hashlib,io,json,math,os
import numpy as np
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/OpalPolishV2'
SEED=641933
GRID=64
MIN_REGION=24
TRANSITION_PX=16

def sha(data):return hashlib.sha256(data).hexdigest()
def png(array):
    stream=io.BytesIO();Image.fromarray(array).save(stream,format='PNG',compress_level=9);return stream.getvalue()
def float_blur(array,radius):
    # Float-mode box-blur support differs across Pillow builds; use 16-bit-equivalent RGB packing
    # only for the deliberately low-frequency authored scalar field (8-bit is ample here).
    image=Image.fromarray(np.round(np.clip(array,0,1)*255).astype('uint8'))
    return np.asarray(image.filter(ImageFilter.GaussianBlur(radius)),dtype=np.float64)/255

def palette_regions(color):
    small=color.resize((GRID,GRID),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(1.15))
    rgb=np.asarray(small,dtype=np.float64)/255
    high=rgb.max(2);low=rgb.min(2);delta=high-low;chroma=delta/np.maximum(high,1e-8)
    hue=np.zeros((GRID,GRID),float)
    for channel in range(3):
        mask=(rgb.argmax(2)==channel)&(delta>1e-8)
        if channel==0:raw=((rgb[:,:,1]-rgb[:,:,2])/np.maximum(delta,1e-8))%6
        elif channel==1:raw=(rgb[:,:,2]-rgb[:,:,0])/np.maximum(delta,1e-8)+2
        else:raw=(rgb[:,:,0]-rgb[:,:,1])/np.maximum(delta,1e-8)+4
        hue[mask]=raw[mask]/6
    classes=np.floor((hue*8+.5)%8).astype('int32')
    classes[chroma<.14]=8
    labels=np.full((GRID,GRID),-1,dtype='int32');regions=[]
    for y in range(GRID):
        for x in range(GRID):
            if labels[y,x]>=0:continue
            identity=len(regions);queue=deque([(y,x)]);labels[y,x]=identity;points=[]
            while queue:
                yy,xx=queue.popleft();points.append((yy,xx))
                for ny,nx in [(yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)]:
                    if 0<=ny<GRID and 0<=nx<GRID and labels[ny,nx]<0 and classes[ny,nx]==classes[yy,xx]:labels[ny,nx]=identity;queue.append((ny,nx))
            coords=np.asarray(points);ys,xs=coords[:,0],coords[:,1]
            regions.append(dict(coords=coords,size=len(points),center=np.array([ys.mean(),xs.mean()])/GRID,color=rgb[ys,xs].mean(0),hue=float(np.angle(np.exp(2j*np.pi*hue[ys,xs]).mean())/(2*np.pi)%1),palette=int(classes[y,x])))
    keep=[i for i,r in enumerate(regions) if r['size']>=MIN_REGION]
    if not keep:keep=[max(range(len(regions)),key=lambda i:regions[i]['size'])]
    for identity,r in enumerate(regions):
        if identity in keep:continue
        # Preserve whole small connected islands; merge to a nearby broad region of similar color.
        target=min(keep,key=lambda i:float(np.sum((r['color']-regions[i]['color'])**2)*4+np.sum((r['center']-regions[i]['center'])**2)*.6))
        labels[r['coords'][:,0],r['coords'][:,1]]=target
    return labels,regions,keep

def main(source_image=None):
    original=Path(source_image).read_bytes() if source_image else (OUT/'Source/OpalOriginal.png').read_bytes()
    color=Image.open(io.BytesIO(original));color.load()
    if color.mode!='RGB':raise RuntimeError('Preserve original: this authoring contract requires an already RGB PNG')
    width,height=color.size;source_pixels=np.asarray(color)
    labels,regions,keep=palette_regions(color);rng=np.random.default_rng(SEED)
    sx=np.zeros((GRID,GRID));sy=np.zeros_like(sx);phase=np.zeros_like(sx);coverage=np.zeros_like(sx);body=np.zeros_like(sx)
    authored_regions=[]
    for identity in keep:
        region=regions[identity];angle=region['hue']*2*math.pi+rng.uniform(-.45,.45)
        magnitude=float(rng.uniform(.18,.28));dx=magnitude*math.cos(angle);dy=magnitude*math.sin(angle);mask=labels==identity
        sx[mask]=dx;sy[mask]=dy;phase[mask]=region['hue']*.82+.08
        rgb=region['color'];chroma=float((rgb.max()-rgb.min())/max(rgb.max(),.001))
        coverage[mask]=np.clip((chroma-.10)/.40,0,1)
        body[mask]=float(rgb.mean())
        authored_regions.append(dict(identity=identity,grid_pixel_count=int(mask.sum()),palette_class=region['palette'],hue=region['hue'],tangent_slope=[dx,dy],slope_magnitude=magnitude))
    def upsample(field):
        # Signed tilt becomes a bounded linear scalar for deterministic image interpolation.
        small=Image.fromarray(np.round(np.clip(field,0,1)*255).astype('uint8'))
        return np.asarray(small.resize((width,height),Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(TRANSITION_PX)),dtype=np.float64)/255
    slope_x=(upsample(sx/.6+.5)-.5)*.6;slope_y=(upsample(sy/.6+.5)-.5)*.6
    length=np.sqrt(slope_x*slope_x+slope_y*slope_y+1)
    normal=np.stack([slope_x/length,slope_y/length,1/length],-1)
    cov=upsample(coverage);bod=upsample(body);spectral_phase=upsample(phase)
    # Roughness is broad and quiet; no luminance gradients create domain orientation.
    roughness=.285+.025*(1-cov)+.006*(bod-.5)
    arrays={'OpalDomains':np.round(np.clip(np.stack([cov,bod,spectral_phase],-1),0,1)*255).astype('uint8'),
            'OpalDomainNormal':np.round((normal*.5+.5)*255).astype('uint8'),
            'OpalPolishNormal':np.broadcast_to(np.array([128,128,255],dtype='uint8'),(height,width,3)).copy(),
            'OpalRoughness':np.round(roughness*255).astype('uint8')}
    pending={'Source/OpalOriginal.png':original,'Textures/OpalColor.png':original};maps={}
    map_arrays={'OpalColor':source_pixels,**arrays}
    for name,array in map_arrays.items():
        relative='Textures/'+name+'.png';data=original if name=='OpalColor' else png(array)
        decoded=np.asarray(Image.open(io.BytesIO(data)))
        if not np.array_equal(decoded,array):raise RuntimeError('PNG pixel roundtrip differs '+name)
        if name not in ['OpalPolishNormal'] and int(array.max())==int(array.min()):raise RuntimeError('Unexpected flat utility '+name)
        pending[relative]=data
        maps[name]=dict(path=relative,sha256=sha(data),width=width,height=height,srgb=name=='OpalColor',channels='RGB' if array.ndim==3 else 'L',bit_depth=data[24],decoded_min=int(array.min()),decoded_max=int(array.max()),decoded_pixel_sha256=sha(array.tobytes()),decoded_roundtrip_verified=True)
    decoded=arrays['OpalDomainNormal'].astype(float)/255*2-1
    decoded_slopes=decoded[:,:,:2]/np.maximum(decoded[:,:,2:3],1e-8)
    report=dict(schema_version=1,generator_source='Tools/UsfMaterials/author_opal_polish_maps.py',generator_sha256=sha(Path(__file__).read_bytes()),
        source=dict(path='Source/OpalOriginal.png',sha256=sha(original),provenance='Original built-in image generation, 2026-10-22. Original RGB artwork, not a scan or measured optics. Utility maps are numerical artist estimates.',generation_image_id='exec-6f70bd07-e659-496b-9121-d0f11029d84d',prompt_support='Source/ImagePrompt.txt',prompt_note='Original generation prompt is supplied by the lead in the separate support file; no prompt has been invented by utility-map authoring.'),
        maps=maps,seed=SEED,color_preservation='Source/OpalOriginal.png and Textures/OpalColor.png are byte-identical copies of the original generated RGB PNG; appearance artwork is unedited.',
        authoring=dict(segmentation='8 broad hue families plus low-chroma body; 4-connected regions on blurred 64x64 color, small islands merged by color and proximity',segmentation_grid=GRID,minimum_region_grid_pixels=MIN_REGION,broad_region_count=len(keep),merged_small_region_count=len(regions)-len(keep),transition_blur_pixels=TRANSITION_PX,orientation='One seeded constant tangent tilt per retained connected broad palette region; smooth boundary interpolation; no brightness-derivative normal, fracture gradient or tiny Voronoi glitter.',normal_convention='DirectX tangent; normalize(slope_u,slope_v,1); original top-left image orientation; no green flip',domain_channels='R=smoothed broad chromatic coverage,G=smoothed broad body value,B=coherent palette spectral-phase artist estimate',polish_normal=[128,128,255],roughness_linear_range=[float(roughness.min()),float(roughness.max())],authored_pretransition_slope_magnitude_range=[min(r['slope_magnitude'] for r in authored_regions),max(r['slope_magnitude'] for r in authored_regions)],decoded_slope_component_min=decoded_slopes.reshape(-1,2).min(0).tolist(),decoded_slope_component_max=decoded_slopes.reshape(-1,2).max(0).tolist(),maximum_decoded_slope_magnitude=float(np.linalg.norm(decoded_slopes,axis=2).max()),regions=authored_regions),
        limitations=['Numerically authored coverage, orientation, phase and roughness are artistic estimates, not calibrated mineral or optical scans.','Smooth tangent orientation is constant over broad color-region interiors; it is not a displacement-derived surface normal.','A flat outer polish normal is intentional. Native response and visual quality still require real rendered verification.'])
    pending['OpalTextures.json']=(json.dumps(report,indent=2)+'\n').encode()
    for relative,data in pending.items():
        path=(OUT/relative).resolve()
        if not path.is_relative_to(OUT.resolve()):raise RuntimeError('Output escaped new resource root')
        if path.exists() and path.read_bytes()!=data:raise RuntimeError('Preserve differing authored output: '+str(path))
    for relative,data in pending.items():
        path=OUT/relative
        if path.exists():continue
        path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.pending')
        with temporary.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        if path.exists():raise RuntimeError('Concurrent authored output appeared')
        temporary.rename(path)
    assert (OUT/'Source/OpalOriginal.png').read_bytes()==(OUT/'Textures/OpalColor.png').read_bytes()==original
    print(json.dumps(dict(receipt=str(OUT/'OpalTextures.json'),dimensions=[width,height],maps=list(maps),regions=len(keep),source_sha256=sha(original),authored_slope_range=report['authoring']['authored_pretransition_slope_magnitude_range'],decoded_slope_min=report['authoring']['decoded_slope_component_min'],decoded_slope_max=report['authoring']['decoded_slope_component_max'],maximum_decoded_slope_magnitude=report['authoring']['maximum_decoded_slope_magnitude']),indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',help='Original built-in generated RGB PNG; omitted only for identical rerun from preserved source');args=parser.parse_args();main(args.source)
