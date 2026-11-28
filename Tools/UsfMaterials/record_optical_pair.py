"""Record the completed optical-pair rendered evidence and generate its review gallery."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
from build_optical_pair_gallery import main as gallery

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'
def read(name):return json.loads((OUT/name).read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pixels(name):return np.asarray(Image.open(OUT/(name+'.png')).convert('RGB'),dtype=np.float32)

def main():
    proof=read('OpticalPair-FreshProof.json');reload=read('OpticalPair-LiveReload.json')
    defaults=read('OpticalPair-SavedDefaults.json');metrics={}
    for role,endpoint in [('Opal','Plain'),('Display','Clear')]:
        prefix='OpticalPair-'+role
        final=pixels(prefix+'-Final')
        metrics[role]={key:float(np.abs(final-pixels(prefix+'-'+key)).mean()) for key in [endpoint,'LightsOff','Angle','Recovered']}
        metrics[role]['lights_off_nonzero_rgb_pixels']=int(np.any(pixels(prefix+'-LightsOff')>0,axis=2).sum())
    assert metrics['Opal']['lights_off_nonzero_rgb_pixels']==0
    assert metrics['Display']['lights_off_nonzero_rgb_pixels']>0
    protected={
        'Config/DefaultEngine.ini':'20d012dff0397da2198fb8af0e7b19dade2f8f204d10c54340f80c5eeb579438',
        'Saved/UsfMaterialGallery/AmberPolish-Final.png':'7c5893f5a053c7cdcfefda09223d388dc85609dab2387f031a3c18a049225b60',
        'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/AmberSpecimen.ush':'277d81292c5aefa92948810869530146d4e7307350a42be30d4b225654808402'}
    for path,pin in protected.items():assert sha(ROOT/path)==pin,path
    for name,record in proof.items():assert sha(OUT/(name+'.png'))==record['sha256'],name
    report=dict(date='2026-10-22',status='Rendered and technically verified; final artistic review remains with the user',
        renderer='Separate process-only Adaptive profile, 4-closure budget, TAA2',fresh_editor_boots=2,
        cpp_changes=False,engine_changes=False,publication=False,owned_editor_closed=True,
        persistent_defaults_verified_before_overrides=True,native_stats={role:data['compiled'] for role,data in defaults['looks'].items()},
        fresh_capture_count=len(proof),motion=dict(frames_per_material=36,fps=12,duration_seconds=3,resolution=[1600,1200],codec='h264',decode_verified=True),
        image_difference_mae_0_to_255=metrics,
        live_reload={role:{key:data[key] for key in ['source','source_restored_sha256','changed_delta','restored_delta']} for role,data in reload.items()},
        preserved_hashes=protected,
        limitations=['Opal uses artist-authored lit body color and native specular flashes, not measured spectral scattering.',
            'Coating is a subtle RGB reflectance approximation; glass uses neutral PNO, not traced entry/exit transport.',
            'Motion clips are appearance evidence, not runtime performance benchmarks.'],
        evidence=['OpticalPair-Preparation.json','OpticalPair-FreshProof.json','OpticalPair-SavedDefaults.json','OpticalPair-LiveReload.json','OpticalPair-MotionProof.json','OpticalPair-Fresh.log'])
    (OUT/'OpticalPair-Receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    gallery()

if __name__=='__main__':main()
