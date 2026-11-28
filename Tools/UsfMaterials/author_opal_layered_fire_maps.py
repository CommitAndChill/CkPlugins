"""Derive numerical opal fields from unchanged original flat RGB artwork.

First run requires --source and --prompt-file from the actual image-generation
request. The source/color PNG bytes are copied exactly. No image appearance edits,
Voronoi appearance synthesis, brightness-derived normals or engine dependency.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import math
import os
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Plugins/CkTests/Resources/CkUsf/OpalLayeredFireV1'
SEED = 80423


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png(array):
    stream = io.BytesIO()
    Image.fromarray(array).save(stream, format='PNG', compress_level=9)
    return stream.getvalue()


def hue_of(rgb):
    high, low = rgb.max(axis=-1), rgb.min(axis=-1)
    delta = np.maximum(high-low, 1e-9)
    channel = rgb.argmax(axis=-1)
    hue = np.where(channel == 0, ((rgb[..., 1]-rgb[..., 2])/delta) % 6,
                   np.where(channel == 1, (rgb[..., 2]-rgb[..., 0])/delta+2,
                            (rgb[..., 0]-rgb[..., 1])/delta+4))/6
    return hue, (high-low)/np.maximum(high, .001)


def segment(rgb):
    """Choose an auditable threshold; do not manufacture extra domains to meet a count."""
    smooth = ndimage.gaussian_filter(rgb, sigma=(.8, .8, 0), mode='nearest')
    hue, chroma = hue_of(smooth)
    min_pixels = max(24, int(round(rgb.shape[0]*rgb.shape[1]*.000035)))
    candidates = []
    for threshold in [.20, .24, .28, .32, .36, .40, .44, .48]:
        mask = (chroma >= threshold) & (smooth.max(2) > .12)
        # Remove isolated chromatic pixels and close only one-pixel antialias gaps.
        mask = ndimage.binary_opening(mask, iterations=1)
        mask = ndimage.binary_closing(mask, iterations=1)
        labels, count = ndimage.label(mask)
        areas = np.bincount(labels.ravel(), minlength=count+1)
        kept = np.flatnonzero(areas >= min_pixels)
        kept = kept[kept != 0]
        table = np.zeros(count+1, dtype=np.int32)
        table[kept] = np.arange(1, len(kept)+1)
        labels = table[labels]
        coverage = float(np.mean(labels > 0))
        candidates.append(dict(threshold=threshold, region_count=len(kept), coverage=coverage,
                               discarded_components=int(count-len(kept)), labels=labels))
    eligible = [value for value in candidates if 150 <= value['region_count'] <= 350 and .20 <= value['coverage'] <= .30]
    summary = [{key: value for key, value in candidate.items() if key != 'labels'} for candidate in candidates]
    if not eligible:
        raise RuntimeError('Actual artwork does not meet connected-island count/coverage; preserve image and review source: '+json.dumps(summary))
    chosen = min(eligible, key=lambda value: abs(value['coverage']-.25)+abs(value['region_count']-250)/2500)
    return chosen, hue, chroma, min_pixels, summary


def main(source=None, prompt_file=None, generation_image_id=None):
    original_path = Path(source) if source else OUT/'Source/OpalOriginal.png'
    original = original_path.read_bytes()
    if original[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError('Preserve original: already RGB PNG required, no format conversion')
    image = Image.open(io.BytesIO(original))
    image.load()
    if image.mode != 'RGB':
        raise RuntimeError('Preserve original: RGB PNG required, no appearance or color-space conversion')
    source_pixels = np.asarray(image)
    rgb = source_pixels.astype(np.float64)/255
    selected, hue, chroma, min_pixels, candidates = segment(rgb)
    labels, count = selected['labels'], selected['region_count']
    rng = np.random.default_rng(SEED)
    centers = np.asarray(ndimage.center_of_mass(np.ones_like(labels), labels, range(1, count+1)))
    means = np.array([[ndimage.mean(rgb[..., channel], labels, index) for channel in range(3)] for index in range(1, count+1)])
    region_hue, region_chroma = hue_of(means)
    families = np.floor(region_hue*8+.5).astype(int) % 8
    # Broad family axes plus small deterministic per-domain variation; neighboring
    # domain families influence direction without deriving tilt from RGB gradients.
    family_angle = np.linspace(.1, 2*math.pi+.1, 8, endpoint=False)+rng.uniform(-.18, .18, 8)
    family_magnitude = rng.uniform(.18, .46, 8)
    family_vectors = np.stack([np.cos(family_angle), np.sin(family_angle)], axis=1)*family_magnitude[:, None]
    nearest = cKDTree(centers).query(centers, k=min(7, count))[1]
    vectors = []
    for index in range(count):
        own = family_vectors[families[index]]
        neighbors = family_vectors[families[nearest[index, 1:]]].mean(0)
        direction = .80*own+.20*neighbors
        angle = math.atan2(direction[1], direction[0])+rng.uniform(-.16, .16)
        magnitude = float(np.clip(np.linalg.norm(direction)*rng.uniform(.84, 1.18), .10, .55))
        vectors.append([math.cos(angle)*magnitude, math.sin(angle)*magnitude])
    vectors = np.asarray(vectors)
    # Extend the nearest actual patch's orientation through neutral gaps. This is
    # label propagation only: it never replaces the artwork or invents patch borders.
    indices = ndimage.distance_transform_edt(labels == 0, return_distances=False, return_indices=True)
    extended = labels[tuple(indices)]-1
    slopes = vectors[extended]
    normal = np.concatenate([slopes, np.ones((*labels.shape, 1))], axis=2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    coverage = np.clip((chroma-(selected['threshold']-.035))/.07, 0, 1)
    coverage *= labels > 0
    body = rgb@np.array([.2126, .7152, .0722])
    phase_by_region = .06+.88*region_hue
    phase = phase_by_region[extended]
    height, width = labels.shape
    arrays = dict(OpalColor=source_pixels,
        OpalDomains=np.rint(np.clip(np.stack([coverage, body, phase], axis=2), 0, 1)*255).astype(np.uint8),
        OpalDomainNormal=np.rint((normal*.5+.5)*255).astype(np.uint8),
        OpalPolishNormal=np.broadcast_to(np.array([128, 128, 255], dtype=np.uint8), (height, width, 3)).copy(),
        OpalRoughness=np.full((height, width), round(.12*255), dtype=np.uint8))
    prompt_path = Path(prompt_file) if prompt_file else OUT/'Source/ImagePrompt.txt'
    if not prompt_path.is_file():
        raise RuntimeError('Exact generation prompt support file required; no prompt is invented')
    prompt = prompt_path.read_bytes()
    if not prompt.strip():
        raise RuntimeError('Generation prompt support must be nonempty')
    pending = {'Source/OpalOriginal.png': original, 'Source/ImagePrompt.txt': prompt}
    maps = {}
    for name, array in arrays.items():
        data = original if name == 'OpalColor' else png(array)
        decoded = np.asarray(Image.open(io.BytesIO(data)))
        if not np.array_equal(decoded, array):
            raise RuntimeError('PNG pixel roundtrip differs: '+name)
        relative = 'Textures/'+name+'.png'
        pending[relative] = data
        maps[name] = dict(path=relative, sha256=sha(data), width=width, height=height, srgb=name == 'OpalColor',
            channels='RGB' if array.ndim == 3 else 'L', bit_depth=data[24], decoded_min=int(array.min()), decoded_max=int(array.max()),
            decoded_pixel_sha256=sha(array.tobytes()), decoded_roundtrip_verified=True)
    decoded = arrays['OpalDomainNormal'].astype(np.float64)/255*2-1
    decoded_length = np.linalg.norm(decoded, axis=2)
    decoded_slopes = decoded[..., :2]/decoded[..., 2:3]
    slope_magnitude = np.linalg.norm(decoded_slopes, axis=2)
    edge = (labels > 0) & ~ndimage.binary_erosion(labels > 0)
    if np.max(np.abs(np.linalg.norm(normal, axis=2)-1)) > 1e-12 or decoded_length.min() < .99 or decoded_length.max() > 1.01:
        raise RuntimeError('Authored/encoded domain normals fail unit-vector QA')
    if slope_magnitude[edge].min() < .085 or slope_magnitude.max() > .57:
        raise RuntimeError('Domain orientation flattened at coverage edges or exceeds slope contract')
    neighbor_cosines = np.sum(vectors* vectors[nearest[:, 1]], axis=1)/(np.linalg.norm(vectors, axis=1)*np.linalg.norm(vectors[nearest[:, 1]], axis=1))
    regions = [dict(identity=index+1, pixel_count=int(np.count_nonzero(labels == index+1)), center_yx=centers[index].tolist(),
        family=int(families[index]), hue=float(region_hue[index]), mean_chroma=float(region_chroma[index]),
        tangent_slope=vectors[index].tolist(), slope_magnitude=float(np.linalg.norm(vectors[index]))) for index in range(count)]
    report = dict(schema_version=1, generator_source='Tools/UsfMaterials/author_opal_layered_fire_maps.py', generator_sha256=sha(Path(__file__).read_bytes()),
        source=dict(path='Source/OpalOriginal.png', sha256=sha(original),
            provenance='Original built-in generated flat RGB artwork. Utility fields are numerical artist estimates, not scanned or measured optics.',
            generation_image_id=generation_image_id, prompt_support='Source/ImagePrompt.txt', prompt_sha256=sha(prompt)),
        maps=maps, seed=SEED,
        color_preservation='Source/OpalOriginal.png and Textures/OpalColor.png preserve original PNG bytes exactly; no appearance editing.',
        authoring=dict(segmentation='Connected chromatic patches from original artwork; binary antialias cleanup only, no appearance synthesis',
            region_count=count, minimum_component_pixels=min_pixels, selected_threshold=selected['threshold'], threshold_candidates=candidates,
            binary_chromatic_coverage=selected['coverage'], mean_coverage=float(coverage.mean()), family_count=int(len(set(families.tolist()))),
            domain_channels='R=actual connected chromatic patch coverage,G=source body value,B=nearest-domain family phase estimate',
            orientation='One deterministic normalized tilt per connected patch; broad families with neighboring-family influence; nearest-patch orientation extends through gaps without coverage multiplication',
            normal_convention='DirectX tangent normalize(slope_u,slope_v,1); original top-left image orientation; no green flip',
            authored_slope_range=[float(np.linalg.norm(vectors, axis=1).min()), float(np.linalg.norm(vectors, axis=1).max())],
            decoded_slope_range=[float(slope_magnitude.min()), float(slope_magnitude.max())],
            coverage_edge_minimum_decoded_slope=float(slope_magnitude[edge].min()),
            maximum_authored_unit_length_error=float(np.max(np.abs(np.linalg.norm(normal, axis=2)-1))),
            decoded_unit_length_range=[float(decoded_length.min()), float(decoded_length.max())],
            nearest_neighbor_orientation_mean_cosine=float(neighbor_cosines.mean()),
            polish_normal=[128, 128, 255], roughness_requested=.12, roughness_encoded=int(round(.12*255)), roughness_decoded=round(.12*255)/255,
            regions=regions),
        limitations=['Coverage, family phase and tilt are numerical artistic estimates, not calibrated mineral structure or optical scans.',
            'Normals describe internal optical domains, not RGB brightness gradients or displaced surface geometry.',
            'Nearest-domain orientation extension changes only numerical fields in gaps; appearance RGB remains unmodified.',
            'Constant roughness .12 is represented by the nearest 8-bit value; outer polish normal is intentionally flat.',
            'Native material response, visual quality and performance require separate real rendered verification.'])
    pending['OpalTextures.json'] = (json.dumps(report, indent=2)+'\n').encode()
    for relative, data in pending.items():
        path = (OUT/relative).resolve()
        if not path.is_relative_to(OUT.resolve()) or path.is_symlink():
            raise RuntimeError('Escaped immutable opal-fire resource destination')
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError('Preserve differing immutable opal-fire output: '+str(path))
    for relative, data in pending.items():
        path = OUT/relative
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name+'.pending')
        with temporary.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        if path.exists():
            raise RuntimeError('Concurrent opal-fire resource appeared')
        temporary.rename(path)
    assert (OUT/'Source/OpalOriginal.png').read_bytes() == (OUT/'Textures/OpalColor.png').read_bytes() == original
    print(json.dumps(dict(manifest=str(OUT/'OpalTextures.json'), manifest_sha256=sha(pending['OpalTextures.json']),
        dimensions=[width, height], regions=count, coverage=selected['coverage'], source_sha256=sha(original),
        authored_slope_range=report['authoring']['authored_slope_range'], decoded_slope_range=report['authoring']['decoded_slope_range'],
        coverage_edge_minimum_slope=report['authoring']['coverage_edge_minimum_decoded_slope']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', help='Original RGB PNG from the actual generation result')
    parser.add_argument('--prompt-file', help='Exact image-generation prompt support text')
    parser.add_argument('--generation-image-id', help='Actual image generation result identifier')
    args = parser.parse_args()
    main(args.source, args.prompt_file, args.generation_image_id)

