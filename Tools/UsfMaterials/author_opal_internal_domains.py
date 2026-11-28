"""Author numerical full-area optical domains; preserve the selected RGB original exactly.

No color artwork generation, recoloring, brightness-derived normal, or engine work.
Source RGB gradients locate existing fine boundaries only; optical tilt is seeded data.
"""
from pathlib import Path
import argparse,hashlib,io,json,math,os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Plugins/CkTests/Resources/CkUsf/OpalInternalDomainsV1'
UPSTREAM=ROOT/'Plugins/CkTests/Resources/CkUsf/OpalPolishV2'
ORIGINAL_SHA='7d66d3ff5ca042e4ffa170eeb844f18aaac921a4bba2d591030b2d41b59660b6'
SEED=804231


def sha(data):return hashlib.sha256(data).hexdigest()

def png(array):
    output=io.BytesIO();Image.fromarray(array).save(output,format='PNG',compress_level=9);return output.getvalue()


def domains(rgb):
    smooth=ndimage.gaussian_filter(rgb,sigma=(.85,.85,0),mode='nearest')
    dx=ndimage.sobel(smooth,axis=1,mode='nearest')
    dy=ndimage.sobel(smooth,axis=0,mode='nearest')
    edge=np.sqrt(np.sum(dx*dx+dy*dy,axis=2))
    # Seed source-interior minima, never a regular grid, palette mask or Voronoi sites.
    minima=(edge==ndimage.minimum_filter(edge,size=45,mode='nearest'))&(edge<=np.quantile(edge,.45))
    components,count=ndimage.label(minima)
    if count<2 or count>5000:raise RuntimeError('Source-interior minima scale requires review: '+str(count))
    centers=ndimage.center_of_mass(minima,components,range(1,count+1))
    markers=np.zeros(edge.shape,dtype=np.int32)
    for index,(y,x) in enumerate(centers,1):markers[int(round(y)),int(round(x))]=index
    cost=np.rint(np.clip(edge/max(float(np.quantile(edge,.995)),1e-8),0,1)*255).astype(np.uint8)
    labels=ndimage.watershed_ift(cost,markers)
    if np.any(labels<=0):raise RuntimeError('Every source pixel must have an explicit optical domain')
    ids=np.unique(labels);table=np.zeros(int(labels.max())+1,dtype=np.int32);table[ids]=np.arange(1,len(ids)+1)
    labels=table[labels];raw_areas=np.bincount(labels.ravel());small=np.flatnonzero((raw_areas>0)&(raw_areas<16));small=small[small!=0]
    # Watershed cost ties can retain one-pixel seed fragments. Merge only these
    # numerical fragments into a SOURCE-ADJACENT plate of closest mean source RGB.
    # This is not nearest-center propagation and never touches RGB appearance.
    means=np.stack([np.bincount(labels.ravel(),weights=rgb[:,:,c].ravel(),minlength=len(raw_areas))/np.maximum(raw_areas,1) for c in range(3)],axis=1)
    slices=ndimage.find_objects(labels)
    for identity in small:
        sy,sx=slices[identity-1];sy=slice(max(0,sy.start-1),min(labels.shape[0],sy.stop+1));sx=slice(max(0,sx.start-1),min(labels.shape[1],sx.stop+1))
        crop=labels[sy,sx];mask=crop==identity;padded=np.pad(crop,1,mode='edge')
        touching=np.concatenate([a[mask] for a in [padded[:-2,1:-1],padded[2:,1:-1],padded[1:-1,:-2],padded[1:-1,2:]]])
        neighbors,shared=np.unique(touching,return_counts=True);valid=(neighbors!=identity)&(raw_areas[neighbors]>=16);neighbors,shared=neighbors[valid],shared[valid]
        if not len(neighbors):raise RuntimeError('Tiny fragment has no non-tiny source-adjacent plate; inspect labels')
        score=np.sum((means[neighbors]-means[identity])**2,axis=1)+.01/shared
        crop[mask]=neighbors[np.argmin(score)]
    ids=np.unique(labels);table=np.zeros(int(labels.max())+1,dtype=np.int32);table[ids]=np.arange(1,len(ids)+1);labels=table[labels]
    areas=np.bincount(labels.ravel())[1:]
    fraction_small=float(np.mean(areas<16))
    if len(areas)>5000 or fraction_small>.05:raise RuntimeError('Tiny optical-cell field requires review; no silent glitter fallback')
    return labels,areas,dict(method='Full-resolution RGB source-edge watershed with local interior-minimum markers; no hue/chroma exclusion, nearest-center partition or RGB alteration',
        prefilter_sigma_pixels=.85,seed_minimum_window_pixels=45,seed_gradient_max_quantile=.45,cost_scale_quantile=.995,
        raw_watershed_regions=int(len(raw_areas)-1),merged_below_16_pixel_fragments=int(len(small)),merged_source_pixel_fraction=float(raw_areas[small].sum()/labels.size),
        region_area_percentiles={str(q):float(np.percentile(areas,q)) for q in [5,10,25,50,75,90,95]},count=int(len(areas)),minimum_region_pixels=int(areas.min()),median_region_pixels=float(np.median(areas)),maximum_region_pixels=int(areas.max()),
        fraction_regions_below_16_pixels=fraction_small,fraction_pixels_in_regions_below_16_pixels=float(areas[areas<16].sum()/areas.sum()),
        maximum_region_area_fraction=float(areas.max()/areas.sum()),unassigned_pixels=0)


def main(preview=False):
    original=(UPSTREAM/'Source/OpalOriginal.png').read_bytes()
    if sha(original)!=ORIGINAL_SHA:raise RuntimeError('Selected original RGB bytes differ; preserve source')
    image=Image.open(io.BytesIO(original));image.load()
    if image.mode!='RGB' or original[:8]!=b'\x89PNG\r\n\x1a\n':raise RuntimeError('Original must already be RGB PNG; conversion forbidden')
    pixels=np.asarray(image);height,width=pixels.shape[:2]
    labels,areas,segmentation=domains(pixels.astype(np.float64)/255)
    count=len(areas);rng=np.random.default_rng(SEED)
    angles=rng.uniform(-math.pi,math.pi,count)
    magnitudes=rng.uniform(.045,.24,count)
    axes=np.stack([np.cos(angles)*magnitudes,np.sin(angles)*magnitudes],axis=1)
    index=labels-1
    # Boundary interpolation acts only on authored numerical tilt, never source RGB.
    slopes=ndimage.gaussian_filter(axes[index],sigma=(.7,.7,0),mode='nearest')
    normal=np.concatenate([slopes,np.ones((height,width,1))],axis=2);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    variation=rng.uniform(.4,.6,count)[index]
    tilt=np.linalg.norm(slopes,axis=2)/.24
    fields=dict(OpalColor=pixels,
        OpalDomains=np.rint(np.stack([np.ones((height,width)),variation,tilt],axis=2)*255).astype(np.uint8),
        OpalDomainNormal=np.rint((normal*.5+.5)*255).astype(np.uint8),
        OpalPolishNormal=np.broadcast_to(np.array([128,128,255],np.uint8),(height,width,3)).copy(),
        OpalRoughness=np.full((height,width),round(.12*255),np.uint8))
    if not np.all(fields['OpalDomains'][:,:,0]==255):raise RuntimeError('Eligibility must be exactly1 over the entire source')
    decoded=fields['OpalDomainNormal'].astype(float)/255*2-1
    unit_error=float(np.max(np.abs(np.linalg.norm(decoded,axis=2)-1)))
    if unit_error>.009 or not np.all(np.isfinite(decoded)):raise RuntimeError('Encoded optical-axis field invalid')
    upstream=json.loads((UPSTREAM/'OpalTextures.json').read_text(encoding='utf-8-sig'))
    prompt=(UPSTREAM/upstream['source']['prompt_support']).read_bytes()
    pending={'Source/OpalOriginal.png':original,'Source/ImagePrompt.txt':prompt}
    maps={}
    for key,array in fields.items():
        data=original if key=='OpalColor' else png(array);decoded_pixels=np.asarray(Image.open(io.BytesIO(data)))
        if not np.array_equal(decoded_pixels,array):raise RuntimeError('Numerical PNG decoded roundtrip differs: '+key)
        relative='Textures/'+key+'.png';pending[relative]=data
        maps[key]=dict(path=relative,sha256=sha(data),width=width,height=height,srgb=key=='OpalColor',channels='RGB' if array.ndim==3 else 'L',bit_depth=8,
            decoded_pixel_sha256=sha(array.tobytes()),decoded_roundtrip_verified=True,decoded_min=int(array.min()),decoded_max=int(array.max()),runtime_name='T_OpalInternal_'+key)
    label_data=png(labels.astype(np.uint16));pending['Data/DomainLabels.png']=label_data
    if not np.array_equal(np.asarray(Image.open(io.BytesIO(label_data))),labels):raise RuntimeError('Domain-label decoded roundtrip differs')
    centers=ndimage.center_of_mass(np.ones_like(labels),labels,range(1,count+1))
    region_data=[dict(id=i+1,pixels=int(areas[i]),center_yx=[float(v) for v in centers[i]],slope_xy=axes[i].tolist(),slope_magnitude=float(magnitudes[i])) for i in range(count)]
    regions=(json.dumps(dict(seed=SEED,regions=region_data),indent=2)+'\n').encode();pending['Data/Regions.json']=regions
    record=dict(schema_version=1,generator_source='Tools/UsfMaterials/author_opal_internal_domains.py',generator_sha256=sha(Path(__file__).read_bytes()),seed=SEED,
        source=dict(path='Source/OpalOriginal.png',sha256=ORIGINAL_SHA,upstream_path=(UPSTREAM/'Source/OpalOriginal.png').relative_to(ROOT).as_posix(),
            provenance='User-selected earlier built-in generated RGB artwork, preserved exactly. Full-area optical orientation/variation are numerical artist estimates, not mineral scans or measured optical data.',
            generation_image_id=upstream['source']['generation_image_id'],prompt_support='Source/ImagePrompt.txt',prompt_sha256=sha(prompt)),
        maps=maps,data_files=[dict(path='Data/DomainLabels.png',sha256=sha(label_data)),dict(path='Data/Regions.json',sha256=sha(regions))],
        color_preservation='Source/OpalOriginal.png and Textures/OpalColor.png preserve the selected original RGB PNG bytes exactly; no generated/recolored/replaced appearance artwork.',
        authoring=dict(segmentation=segmentation,eligibility=dict(minimum=1,maximum=1,eligible_fraction=1,excluded_pixels=0),
            domain_channels='R=constant1 eligibility/check only; G=mild seeded optical-thickness variation [.4,.6]; B=authored optical-axis tilt magnitude normalized by .24; no viewgate or spectralphase',
            orientation='One deterministic seeded constant tangent tilt per full-area source-boundary region; .7-pixel numerical boundary interpolation. Brightness gradients locate boundaries only, never define tilt.',
            normal_convention='DirectX tangent normalize(slope_x,slope_y,1), original image orientation, no green flip; reflector B only, independent smooth coat A and cloudy medium C.',
            authored_slope_magnitude_range=[float(magnitudes.min()),float(magnitudes.max())],maximum_decoded_unit_length_error=unit_error,
            polish_normal=[128,128,255],roughness=round(.12*255)/255),
        limitations=['Optical axes and thickness variation are deterministic artist data, not inferred physical crystal normals.','The unchanged source contains its original artistic RGB pattern; no new colors or background edits were made.','Full-area eligibility is a data invariant, not proof of native rendering, light transport, temporal stability, or visual approval.'])
    pending['OpalTextures.json']=(json.dumps(record,indent=2)+'\n').encode()
    if preview:
        print(json.dumps(dict(preview_only=True,dimensions=[width,height],segmentation=segmentation,eligibility_fraction=1,source_sha256=ORIGINAL_SHA),indent=2));return
    # Preflight the entire immutable output batch before writing any new resource.
    for relative,data in pending.items():
        target=OUT/relative
        if target.exists() and target.read_bytes()!=data:raise RuntimeError('Preserve differing existing numerical resource: '+str(target))
    for relative,data in pending.items():
        target=OUT/relative
        if target.exists():continue
        target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.pending')
        with temporary.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        if target.exists():raise RuntimeError('Concurrent resource appeared; preserve it')
        temporary.rename(target)
    if (OUT/'Source/OpalOriginal.png').read_bytes()!=(OUT/'Textures/OpalColor.png').read_bytes() or sha((UPSTREAM/'Source/OpalOriginal.png').read_bytes())!=ORIGINAL_SHA:raise RuntimeError('Original RGB preservation failed')
    print(json.dumps(dict(manifest=str(OUT/'OpalTextures.json'),manifest_sha256=sha(pending['OpalTextures.json']),dimensions=[width,height],segmentation=segmentation,eligibility_fraction=1,source_sha256=ORIGINAL_SHA),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--preview',action='store_true',help='Compute and validate numerical fields without writing resources')
    main(preview=parser.parse_args().preview)
