"""Cache official CC0 river-pebble source comparisons and one aligned2K set.

No Unreal import, geometry authoring or image synthesis. Cached bytes are pinned
and never overwritten; --research downloads only small candidate color/height.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import source_batch2_textures as source

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT/'Plugins/CkTests/Resources/CkUsf/PebbleReferenceV1'
CANDIDATES = ['ganges_river_pebbles', 'dry_river_pebbles', 'clean_pebbles']
SELECTED = 'ganges_river_pebbles'
LOOK = 'EnvironmentRiverPebbles'


def record(output, aid):
    result={}
    for kind in ['info','files']:
        path=output/'Metadata'/(aid+'_'+kind+'.json')
        result[kind]=json.loads(source.cached(path,'https://api.polyhaven.com/'+kind+'/'+aid))
    return result


def download(output, descriptor, relative):
    path=output/relative;data=source.cached(path,descriptor['url'])
    if len(data)!=descriptor['size'] or hashlib.md5(data).hexdigest()!=descriptor['md5']:
        raise RuntimeError('Publisher integrity mismatch: '+relative)
    return data


def png_sheet(output, records, name, detail=False):
    canvas=source.Image.new('RGB',(len(records)*512,1080),(27,29,32));draw=source.ImageDraw.Draw(canvas)
    for column,(aid,paths) in enumerate(records.items()):
        for row,channel in enumerate(['BaseColor','Height']):
            im=source.Image.open(output/paths[channel])
            if im.mode.startswith('I'):
                a=source.np.asarray(im,dtype=float);im=source.Image.fromarray(source.np.rint(a/257).astype('uint8'))
            if detail:
                w,h=im.size;im=im.crop((w//4,h//4,w*3//4,h*3//4))
            canvas.paste(im.convert('RGB').resize((512,512),source.Image.Resampling.LANCZOS),(column*512,row*540+28))
            draw.text((column*512+8,row*540+8),aid+' / '+channel,fill='white')
    buffer=io.BytesIO();canvas.save(buffer,format='PNG');source.immutable(output/name,buffer.getvalue())


def height_fit(output,maps):
    np=source.np
    h=np.asarray(source.Image.open(output/maps['Height']['path'])).astype(float)/65535
    n=np.asarray(source.Image.open(output/maps['Normal']['path']).convert('RGB')).astype(float)/255*2-1
    x=-(np.roll(h,-1,1)-np.roll(h,1,1))*h.shape[1]/2
    y=-(np.roll(h,-1,0)-np.roll(h,1,0))*h.shape[0]/2
    a=n[:,:,0]/np.maximum(n[:,:,2],.1);b=n[:,:,1]/np.maximum(n[:,:,2],.1)
    valid=(n[:,:,2]>.85)&((x*x+y*y)>.03)&((x*x+y*y)<2000)
    valid[:3]=False;valid[-3:]=False;valid[:,:3]=False;valid[:,-3:]=False
    for _ in range(4):
        ratio=float((x*a+y*b)[valid].sum()/(x*x+y*y)[valid].sum())
        error=np.sqrt((a-ratio*x)**2+(b-ratio*y)**2)
        median=np.median(error[valid]);mad=np.median(abs(error[valid]-median))
        valid &= error<median+3*1.4826*mad
    return {'method':'Through-zero joint leastsquares N.xy/N.z against negative centralHgradient pernormalizedUV, Nz>.85, gradientnorm2 between.03and2000,3pxborderexcluded;4passes3MADresidualtrimming. Normal decodedPillowRGB8; originalRGB16 bytes remain untouched.',
            'height_std':float(h.std()),'height_percentiles':dict(zip(['0','1','5','25','50','75','95','99','100'],np.percentile(h,[0,1,5,25,50,75,95,99,100]).tolist())),
            'relative_height_to_width_fit':ratio,'suggested_full_height_amplitude_at80cm_cm':80*ratio,'fit_pixels':int(valid.sum()),'median_slope_residual':float(np.median(error[valid])),
            'R_G_correlations':[float(np.corrcoef(a[valid],x[valid])[0,1]),float(np.corrcoef(b[valid],y[valid])[0,1])],
            'limit':'Normal-consistency estimate, not physical or optical calibration. Source microsurface/finite differences/filtering differ. Runtime5-6cm is authored; renderedPOM/displacement remains unverified.'}


def selected_sheet(output,maps,detail):
    canvas=source.Image.new('RGB',(1280,286),(27,29,32));draw=source.ImageDraw.Draw(canvas)
    for i,key in enumerate(['BaseColor','Normal','Roughness','Height','AO']):
        im=source.Image.open(output/maps[key]['path'])
        if im.mode.startswith('I'):im=source.Image.fromarray(source.np.rint(source.np.asarray(im,dtype=float)/257).astype('uint8'))
        if detail:im=im.crop((768,768,1280,1280))
        canvas.paste(im.convert('RGB').resize((256,256),source.Image.Resampling.LANCZOS),(i*256,25));draw.text((i*256+5,5),SELECTED+'/'+key,fill='white')
    buffer=io.BytesIO();canvas.save(buffer,format='PNG');source.immutable(output/('SourceDetailContactSheet.png' if detail else 'SourceMapContactSheet.png'),buffer.getvalue())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=DEFAULT);parser.add_argument('--research',action='store_true');args=parser.parse_args();output=args.output.resolve()
    license_path=output/'License/polyhaven.html';license_data=source.cached(license_path,'https://polyhaven.com/license')
    if b'CC0' not in license_data:raise RuntimeError('Official CC0 license statement missing')
    candidates={};metadata={}
    for aid in CANDIDATES:
        r=record(output,aid);metadata[aid]=r;candidates[aid]={}
        for channel,upstream,fmt in [('BaseColor','Diffuse','jpg'),('Height','Displacement','png')]:
            d=r['files'][upstream]['1k'][fmt];rel='Candidates/'+aid+'/'+d['url'].rsplit('/',1)[1]
            download(output,d,rel);candidates[aid][channel]=rel
    png_sheet(output,candidates,'CandidateContactSheet.png');png_sheet(output,candidates,'CandidateDetailSheet.png',True)
    if args.research:
        print('Candidate images ready:',output/'CandidateContactSheet.png');return
    r=metadata[SELECTED];maps={};originals={};planned=0
    for channel,upstream in source.POLY_SUFFIX.items():
        d=r['files'][upstream]['2k']['png'];planned+=d['size']
    if planned>80_000_000:raise RuntimeError('Focused selected-map budget exceeded')
    for channel,upstream in source.POLY_SUFFIX.items():
        d=r['files'][upstream]['2k']['png'];rel='pebbles/Original/'+d['url'].rsplit('/',1)[1]
        data=download(output,d,rel);originals[channel]={'path':rel,'sha256':source.sha256(data),'source_url':d['url'],'upstream_md5':d['md5'],'bytes':len(data)}
        maps[channel]=source.save_map(output,'pebbles',LOOK,channel,data,{'source_url':d['url'],'modifications':'None; original aligned publisher2K PNG bytes; no new grain, height remapping or resampling.'})
    info=r['info'];material={'asset_id':SELECTED,'look_id':LOOK,'provider':'polyhaven','source_url':'https://polyhaven.com/a/'+SELECTED,'author':info['authors'],'license':'CC0-1.0','description':info['description'],'official_tags':info['tags'],'coverage_cm':{'x':info['dimensions'][0]/10,'y':info['dimensions'][1]/10},'coverage_note':'Official dimensions in millimeters converted to cm. This defines source XY coverage, not calibrated displacement amplitude.','maps':maps,'originals':originals,'identity_notes':'Actual mixed river-pebble photogrammetric ground source; evaluated against rounded dense mixed-size reference. Source selection is not UE/POM or visual acceptance.',
        'author_method_evidence':{'url':'https://amalbubble.artstation.com/projects/PXg36L','title':'Ganges River Pebbles - Free Photoscanned Material','verified_statement':'Author identifies it as a photoscanned material made for Poly Haven; lists CanonM6MarkII/EF-M28mm/GodoxAR400 capture hardware.'},
        'presentation_contract':{'runtime_width_cm':80,'runtime_height_cm':80,'uv_tiling':1,'note':'Authored scaled-down presentation of complete216cm scan at80cm; original sourcebytes and XYmetadata unchanged. Relief default5-6cm authored, not measured.'},'normal_height_fit':height_fit(output,maps)}
    selected_paths={SELECTED:{k:v['path'] for k,v in maps.items()}}
    png_sheet(output,selected_paths,'SelectedColorHeightSheet.png');png_sheet(output,selected_paths,'SelectedColorHeightDetail.png',True)
    selected_sheet(output,maps,False);selected_sheet(output,maps,True)
    path=output/'Manifest.json';pins=json.loads(path.read_text()) if path.exists() else None
    manifest={'schema_version':1,'retrieved_utc':pins['retrieved_utc'] if pins else datetime.now(timezone.utc).isoformat(),'generator_source':'Tools/UsfMaterials/source_pebble_reference.py','generator_sha256':source.sha256(Path(__file__).read_bytes()),'required_helper':'Tools/UsfMaterials/source_batch2_textures.py','required_helper_sha256':source.sha256(Path(source.__file__).read_bytes()),'maps_root':output.relative_to(ROOT).as_posix(),'materials':{'pebbles':material},'licenses':[{'provider':'polyhaven','spdx':'CC0-1.0','url':'https://polyhaven.com/license','path':'License/polyhaven.html','sha256':source.sha256(license_data)}],'metadata':{aid:{kind:{'path':'Metadata/'+aid+'_'+kind+'.json','sha256':source.sha256((output/'Metadata'/(aid+'_'+kind+'.json')).read_bytes())} for kind in ['info','files']} for aid in CANDIDATES},'source_bytes_selected':planned,'height_contract':'Original aligned linear16-bit publisher-relative displacement. Increasing values mean higher relief. Physical centimeter amplitude/zero plane are authored separately; no derived height from BC and no geometry/POM acceptance claim.','comparison':'Candidate actual1Kcolor+height maps retained. Selected2Koriginals and canonical byte-identical maps retained. No previous Environment2 or Woodland bytes changed.','verification_scope':'OfficialCC0/metadata snapshots, publisherMD5/size and SHA256, aligneddimensions/normalDX, source map inspection; no import or native render.'}
    manifest['selection_review']={'best_reason':'ActualsourceBC showsdense roundedmixedsizegray/cream/russet/purplestones; alignedheight showsindividualroundedcaps/deepgaps, closestactualmapmatchtoreference.','strongest_counterargument':'Someangularstones/finegritremain; sourceheight lacksphysicalcmcalibration and sourcealone cannotprove deep reference-likePOM.','alternatives':'dry_river_pebbles moreangularandbrownuniform; clean_pebbles muchsmaller/moreuniform stones. Actualcolor/heightcomparisons retained.'}
    source.immutable(path,(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode());print('Selected source bytes',planned,'Manifest SHA256',source.sha256(path.read_bytes()))


if __name__=='__main__':main()
