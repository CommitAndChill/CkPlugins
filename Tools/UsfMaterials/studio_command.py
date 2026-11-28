"""Submit one command to an already imported studio_session, without desktop input."""
import argparse
import json
from pathlib import Path
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['state', 'gc', 'prepare', 'library_prepare', 'aluminum_prepare', 'batch2_prepare', 'batch3_prepare', 'batch4_prepare', 'batch5_prepare', 'batch6_prepare', 'batch7_prepare', 'environment1_prepare', 'environment2_prepare', 'woodland_prepare', 'river_pebbles_prepare', 'diorama_prepare', 'native_bsdf_prepare', 'advanced_bsdf_prepare', 'advanced_bsdf_refine', 'native_toon_profile', 'orbit_on', 'orbit_off', 'orbit_pause', 'orbit_resume', 'orbit_phase', 'orbit_reset', 'orbit_intensity', 'orbit_respawn', 'environment1_grid_state', 'environment_dither_begin', 'environment_dither_end', 'batch6_texture_state', 'plastic_fill_on', 'plastic_fill_off', 'glass_pane_begin', 'glass_pane_end', 'surface_pane_begin', 'surface_pane_end', 'open', 'capture', 'select', 'end', 'quit', 'refresh', 'proof_begin', 'library_proof_begin', 'environment_proof_begin', 'proof_end', 'cost', 'library_cost', 'preview_quality', 'restore_quality'])
    parser.add_argument('--look', choices=['LibrarySilk', 'LibraryLeather', 'LibraryTile', 'LibraryOak', 'LibraryAluminum', 'LibraryPlastic', 'LibraryCanvas', 'LibrarySuede', 'LibraryTerracotta', 'LibraryMarble', 'LibraryRubber', 'LibraryGlass', 'LibraryVelvet', 'LibraryWalnut', 'LibraryGranite', 'LibraryBrass', 'LibraryFrostedGlass', 'LibraryCarbonFiber', 'LibraryKnit', 'LibraryPatentLeather', 'LibraryPorcelain', 'LibraryTerrazzo', 'LibraryTranslucentPlastic', 'LibraryCork', 'LibraryDenim', 'LibraryConcrete', 'LibraryBrick', 'LibraryStainlessSteel', 'LibraryPlywood', 'LibraryCardboard', 'LibraryLinen', 'LibrarySmoothLeather', 'LibraryMosaic', 'LibraryPine', 'LibraryLimestone', 'LibraryGalvanizedSteel',
        'LibraryNylon', 'LibrarySlate', 'LibraryCopper', 'LibraryGlossyPlastic', 'LibraryWax', 'LibraryFiberglass', 'NativePorcelainSlab', 'NativeCeramicToon', 'NativeRubyVelvet', 'NativeVarnishedWalnut', 'NativeResinCarbon', 'NativeCopper'])
    parser.add_argument('--scalar', action='append', default=[], help='Named material override, e.g. UVRotation=90')
    parser.add_argument('--environment', choices=['pom', 'displacement', 'grass_pom', 'grass_displacement',
                                               'dirt_pom', 'dirt_displacement', 'mud_pom', 'mud_displacement'])
    parser.add_argument('--vector', action='append', default=[], help='Named linear RGBA override, e.g. TintColor=1,1,1,1')
    parser.add_argument('--lighting', choices=['studio', 'point'])
    parser.add_argument('--shot', action='store_true', help='Capture the ordinary game viewport with temporal rendering')
    parser.add_argument('--intensity', type=float, default=0)
    parser.add_argument('--phase', type=float, default=0)
    parser.add_argument('--preset', type=int, default=1)
    parser.add_argument('--name', default='Industrial.png')
    parser.add_argument('--distance', type=float, default=210)
    parser.add_argument('--side', type=float, default=0)
    parser.add_argument('--height', type=float, default=35)
    parser.add_argument('--roll', type=float, default=0)
    parser.add_argument('--debug', type=float)
    parser.add_argument('--mask-tiling', type=float)
    parser.add_argument('--wetness', type=float)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[2] / 'Saved/UsfMaterialGallery'
    request = directory / 'StudioRequest.json'
    result = directory / 'StudioResult.json'
    if request.exists():
        raise RuntimeError('Another studio command is queued')
    request_id = str(uuid.uuid4())
    payload = {key: value for key, value in vars(args).items() if value is not None and key != 'report'}
    payload['id'] = request_id
    payload['parameters'] = {key: float(value) for key, value in (item.split('=', 1) for item in args.scalar)}
    payload['vectors'] = {key: list(map(float, value.split(','))) for key, value in (item.split('=', 1) for item in args.vector)}
    temporary = request.with_suffix('.pending')
    temporary.write_text(json.dumps(payload))
    temporary.replace(request)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if result.exists() and not request.exists():
            try:
                data = json.loads(result.read_text())
            except json.JSONDecodeError:
                time.sleep(0.1)
                continue
            if data.get('id') != request_id:
                time.sleep(0.1)
                continue
            if args.report:
                args.report.write_text(json.dumps(data, indent=2))
            print(json.dumps(data, indent=2))
            if not data.get('ok'):
                raise SystemExit(1)
            return
        time.sleep(0.25)
    raise RuntimeError('Studio command timed out; inspect existing editor/log before retrying')


if __name__ == '__main__':
    main()
