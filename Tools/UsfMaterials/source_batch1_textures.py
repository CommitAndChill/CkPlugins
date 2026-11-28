"""Fetch and verify six focused CC0 ambientCG/Poly Haven sets; never imports into Unreal.

Python 3 + Pillow + NumPy. Default 1K PNG originals are retained in Archives.
The existing Manifest.json pins subsequent runs. Changed sources are rejected.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import urllib.parse
import urllib.request
import zipfile

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "Plugins/CkTests/Resources/CkUsf/Batch1Textures"
LICENSE_URL = "https://docs.ambientcg.com/license/"
SELECTION = {
    "silk": ("LibrarySilk", "crepe_satin", "Official Poly Haven fine silk/crepe/satin asset; sourced by source_satin."),
    "leather": ("LibraryLeather", "Leather037", "Clean dark brown leather; inspect source pores for pebbled leather suitability."),
    "tile": ("LibraryTile", "Tiles032", "Clean reflective green glazed subway tiles. Grout mask is derived from this exact source height map."),
    "oak": ("LibraryOak", "Wood049", "Official oak/furniture/smooth wood identity. Finishing is a shader coat over authored oak grain, not baked into new invented grain."),
    "aluminum": ("LibraryAluminum", "Metal051A", "Official aluminum/brushed source with circular brushing. Texture does not establish a uniform linear brush tangent."),
    "plastic": ("LibraryPlastic", "Plastic013A", "White authored plastic surface; matte molded appearance is a shader finish rather than certified polymer/molding-process provenance."),
}
SUFFIXES = {"BaseColor": "Color", "Normal": "NormalDX", "Roughness": "Roughness",
            "Height": "Displacement", "AO": "AmbientOcclusion"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def store_immutable(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError("Refusing changed owned source: " + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def fetch(url):
    if urllib.parse.urlparse(url).scheme != "https":
        raise RuntimeError("HTTPS source required")
    req = urllib.request.Request(url, headers={"User-Agent": "CkMaterialLibrary/1.0 (CC0 texture source evaluation)"})
    with urllib.request.urlopen(req, timeout=90) as response:
        host = urllib.parse.urlparse(response.url).hostname
        if host not in {"ambientcg.com", "docs.ambientcg.com", "acg-download.struffelproductions.com",
                        "polyhaven.com", "api.polyhaven.com", "dl.polyhaven.org"}:
            raise RuntimeError("Unexpected download host: " + str(host))
        return response.read()


def image_record(data, channel):
    image = Image.open(io.BytesIO(data))
    image.load()
    if not (min(image.size) >= 1000 and max(image.size) <= 1100):
        raise RuntimeError("Expected a roughly 1K source image, retaining upstream aspect")
    source_mode = image.mode
    if image.mode == "P":
        image = image.convert("RGB")
    decoded = np.asarray(image)
    values = decoded.astype(np.float64)
    # PNG IHDR depth describes the source, not Pillow's decoded RGB representation.
    # RGB16 becomes uint8; grayscale16 remains uint16 (or int32 with older Pillow).
    depth = data[24]
    limit = 65535.0 if depth == 16 and decoded.dtype.itemsize > 1 else 255.0
    linear = values / limit
    rec = {"sha256": digest(data), "bytes": len(data), "width": image.width,
           "height": image.height, "mode": image.mode, "source_mode": source_mode, "bit_depth": depth,
           "decoded_dtype": str(decoded.dtype), "statistics_divisor": limit,
           "color_space": "sRGB" if channel == "BaseColor" else "linear",
           "normal_convention": "DirectX tangent space (+X,-Y,+Z); do not flip green on import" if channel == "Normal" else None,
           "channel_mean": np.atleast_1d(linear.mean(axis=(0, 1))).tolist(),
           "channel_stddev": np.atleast_1d(linear.std(axis=(0, 1))).tolist(),
           "import_settings": {"sRGB": channel == "BaseColor",
                               "compression": "TC_Normalmap" if channel == "Normal" else ("TC_Default" if channel == "BaseColor" else "TC_Masks"),
                               "address_x": "Wrap", "address_y": "Wrap",
                               "mips": "TMGS_SimpleAverage", "flip_green_channel": False}}
    # These compare actual neighboring wrap texels, not duplicated edge equality.
    rec["wrap_step_mean"] = {"x": float(np.abs(linear[:, 0] - linear[:, -1]).mean()),
                             "y": float(np.abs(linear[0] - linear[-1]).mean())}
    rec["interior_step_mean"] = {"x": float(np.abs(np.diff(linear, axis=1)).mean()),
                                 "y": float(np.abs(np.diff(linear, axis=0)).mean())}
    return rec


def source_material(key, output, pins):
    if key == "silk":
        return key, source_satin(output, pins)
    look, aid, notes = SELECTION[key]
    metadata_path = output / "Metadata" / (aid + ".json")
    api_url = "https://ambientcg.com/api/v2/full_json?" + urllib.parse.urlencode({"id": aid, "include": "tagData,displayData,downloadData,dimensionsData"})
    if metadata_path.exists():
        metadata_data = metadata_path.read_bytes()
    else:
        metadata_data = fetch(api_url)
        store_immutable(metadata_path, metadata_data)
    raw = json.loads(metadata_data)
    assets = raw["foundAssets"]
    if len(assets) != 1 or assets[0]["assetId"] != aid:
        raise RuntimeError("Expected exactly the selected official asset: " + aid)
    asset = assets[0]
    downloads = asset["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
    package = next(item for item in downloads if item["attribute"] == "1K-PNG")
    archive_path = output / "Archives" / package["fileName"]
    archive = archive_path.read_bytes() if archive_path.exists() else fetch(package["downloadLink"])
    if len(archive) != package["size"]:
        raise RuntimeError("Official archive length mismatch: " + aid)
    if pins and pins["materials"][key]["archive"]["sha256"] != digest(archive):
        raise RuntimeError("Pinned archive hash mismatch: " + aid)
    store_immutable(archive_path, archive)
    record = {"look_id": look, "asset_id": aid, "source_url": "https://ambientcg.com/a/" + aid,
              "api_url": api_url, "metadata_path": metadata_path.relative_to(output).as_posix(),
              "metadata_sha256": digest(metadata_data), "author": "ambientCG / Lennart Demes (site operator; no separate per-asset author field)",
              "author_source": "https://docs.ambientcg.com/legal/", "license": "CC0-1.0",
              "creation_method": asset["creationMethod"], "release_date": asset["releaseDate"],
              "official_tags": asset["tags"], "identity_notes": notes,
              "coverage_cm": {axis: asset.get("dimension" + axis.upper()) for axis in "xyz"},
              "coverage_note": "Zero means unspecified by upstream; do not infer real-world scale.",
              "archive": {"path": archive_path.relative_to(output).as_posix(), "sha256": digest(archive), "bytes": len(archive), "url": package["downloadLink"]},
              "maps": {}}
    with zipfile.ZipFile(io.BytesIO(archive)) as package_zip:
        if package_zip.testzip() is not None:
            raise RuntimeError("ZIP CRC validation failed: " + aid)
        names = package_zip.namelist()
        for channel, suffix in SUFFIXES.items():
            name = aid + "_1K-PNG_" + suffix + ".png"
            if name not in names:
                if channel in {"BaseColor", "Normal", "Roughness"}:
                    raise RuntimeError("Missing required map " + name)
                continue
            data = package_zip.read(name)
            path = output / key / "Maps" / (channel + ".png")
            store_immutable(path, data)
            entry = image_record(data, channel)
            entry.update({"path": path.relative_to(output).as_posix(), "archive_member": name,
                          "modifications": "None; byte-identical upstream PNG"})
            record["maps"][channel] = entry
    return key, record


def encode_png(pixels):
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


def source_satin(output, pins):
    files_path = output / "Metadata/crepe_satin_files.json"
    info_path = output / "Metadata/crepe_satin_info.json"
    for kind, path in [("files", files_path), ("info", info_path)]:
        if not path.exists():
            store_immutable(path, fetch("https://api.polyhaven.com/" + kind + "/crepe_satin"))
    files = json.loads(files_path.read_text())
    info = json.loads(info_path.read_text())
    record = {"look_id": "LibrarySilk", "asset_id": "crepe_satin",
              "source_url": "https://polyhaven.com/a/crepe_satin", "license": "CC0-1.0",
              "author": info["authors"], "identity_notes": info["description"],
              "official_tags": info["tags"], "coverage_cm": {"x": info["dimensions"][0] / 10, "y": info["dimensions"][1] / 10},
              "coverage_note": "Upstream dimensions are millimeters; retained non-square maps are 1024x1042.",
              "metadata_path": info_path.relative_to(output).as_posix(), "metadata_sha256": digest(info_path.read_bytes()),
              "files_metadata_sha256": digest(files_path.read_bytes()), "maps": {}, "originals": {}}
    channels = {"BaseColor": "Diffuse", "Normal": "nor_dx", "Roughness": "Rough", "Height": "Displacement",
                "AO": "AO", "Rotation": "anisotropy_rotation", "Anisotropy": "anisotropy_strength"}
    rotation = None
    for channel, upstream in channels.items():
        descriptor = files[upstream]["1k"]["png"]
        original = output / "silk/Original" / descriptor["url"].rsplit("/", 1)[1]
        data = original.read_bytes() if original.exists() else fetch(descriptor["url"])
        if len(data) != descriptor["size"] or hashlib.md5(data).hexdigest() != descriptor["md5"]:
            raise RuntimeError("Official Poly Haven source integrity mismatch: " + channel)
        store_immutable(original, data)
        image = Image.open(io.BytesIO(data))
        source_values = np.asarray(image)
        if image.mode in {"I", "I;16", "I;16B", "I;16L"}:
            values = source_values.astype(np.float64) / 65535.0
            processed = np.rint(values * 255).astype(np.uint8)
        else:
            # Pillow decodes RGB16 PNGs into RGB8, preserving the high eight bits.
            values = source_values.astype(np.float64) / 255.0
            processed = source_values.astype(np.uint8)
        record["originals"][channel] = {"path": original.relative_to(output).as_posix(), "sha256": digest(data),
                                          "url": descriptor["url"], "upstream_md5": descriptor["md5"], "bit_depth": data[24]}
        if channel == "Rotation":
            rotation = values
            continue
        encoded = encode_png(processed)
        path = output / "silk/CrepeSatinMaps" / (channel + ".png")
        store_immutable(path, encoded)
        entry = image_record(encoded, channel)
        entry.update({"path": path.relative_to(output).as_posix(), "modifications": "Original PNG decoded to 8-bit without resizing or inventing detail; grayscale16 uses round(value/257), RGB16 retains high eight bits."})
        record["maps"][channel] = entry
    theta = rotation * (2 * np.pi)
    direction = np.stack([(1 + np.cos(2 * theta)) * 0.5, (1 + np.sin(2 * theta)) * 0.5,
                          np.ones_like(theta)], axis=-1)
    data = encode_png(np.rint(direction * 255).astype(np.uint8))
    path = output / "silk/CrepeSatinMaps/Direction.png"
    store_immutable(path, data)
    entry = image_record(data, "Direction")
    entry.update({"path": path.relative_to(output).as_posix(),
                  "packing": "R=(1+cos(2theta))/2 G=(1+sin(2theta))/2 B=1 confidence; theta=2*pi*upstream_rotation. Decode theta=.5*atan2(2G-1,2R-1).",
                  "source_sha256": record["originals"]["Rotation"]["sha256"],
                  "modifications": "Axial direction encoding of upstream authored turns; no invented fiber pattern."})
    record["maps"]["Direction"] = entry
    record["rotation_convention"] = {"upstream": "0..1 is one full turn; theta=2*pi*value relative to UV tangent",
                                      "verification": "Official crepe_satin_1k.blend connects Non-Color anisotropy_rotation directly to Principled Anisotropic Rotation, and Non-Color anisotropy_strength directly to Anisotropic. Read-only headless Blender node inspection.",
                                      "reference": "https://docs.blender.org/manual/en/4.0/render/shader_nodes/shader/principled.html",
                                      "limitation": "Exact lobe handedness/90-degree principal-axis agreement between Blender and Unreal still requires rendered inspection; BrushRotation is the explicit adjustment."}
    return record


def derive_tile_mask(output, materials):
    record = materials["tile"]
    height = np.asarray(Image.open(output / record["maps"]["Height"]["path"]), dtype=np.float64) / 65535.0
    t = np.clip((height - 0.60) / 0.22, 0, 1)
    pixels = np.rint(t * t * (3 - 2 * t) * 255).astype(np.uint8)
    data = encode_png(pixels)
    path = output / "tile/Maps/Mask.png"
    store_immutable(path, data)
    entry = image_record(data, "Mask")
    entry.update({"path": path.relative_to(output).as_posix(), "packing": "R/grayscale:1=glazed tile,0=grout, fractional values=source bevel transition",
                  "modifications": "smoothstep(.60,.82,upstream_displacement/65535); aligned pixel-for-pixel, no procedural grid",
                  "source_sha256": record["maps"]["Height"]["sha256"],
                  "fraction_glaze_above_half": float((pixels > 127).mean())})
    record["maps"]["Mask"] = entry


def derive_aluminum_direction(output, materials):
    record = materials["aluminum"]
    height = np.asarray(Image.open(output / record["maps"]["Height"]["path"]), dtype=np.float64) / 65535.0
    nx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    ny = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    h, w = nx.shape
    sigma = 4.0
    fx, fy = np.fft.rfftfreq(w)[None, :], np.fft.fftfreq(h)[:, None]
    kernel = np.exp(-2 * np.pi**2 * sigma**2 * (fx**2 + fy**2))
    def gaussian(field):
        return np.fft.irfft2(np.fft.rfft2(field) * kernel, s=(h, w))
    a, b, c = gaussian(nx * nx), gaussian(nx * ny), gaussian(ny * ny)
    gap = np.sqrt(np.maximum((a - c)**2 + 4 * b**2, 0))
    trace = np.maximum(a + c, 0)
    confidence = np.clip(gap / (trace + 1e-14), 0, 1)
    slope_angle = 0.5 * np.arctan2(2 * b, a - c)
    tangent = slope_angle + np.pi * 0.5
    direction = np.stack([(1 + np.cos(2 * tangent)) * 0.5, (1 + np.sin(2 * tangent)) * 0.5, confidence], axis=-1)
    pixels = np.rint(direction * 255).astype(np.uint8)
    data = encode_png(pixels)
    path = output / "aluminum/Maps/DirectionFromHeight.png"
    store_immutable(path, data)
    entry = image_record(data, "Direction")
    entry.update({"path": path.relative_to(output).as_posix(),
                  "packing": "R=(1+cos(2theta))/2,G=(1+sin(2theta))/2,B=structure-tensor confidence. Decode theta=.5*atan2(2G-1,2R-1).",
                  "modifications": "Periodic central differences of original normalized16-bit Height provide actual source slopes. Periodic Gaussian sigma4px smooths gx^2,gx*gy,gy^2. Dominant eigenvector is slope; brush tangent is its perpendicular. Confidence=(lambdaMax-lambdaMin)/(lambdaMax+lambdaMin+1e-14). No invented radial centers.",
                  "source_sha256": record["maps"]["Height"]["sha256"], "gaussian_sigma_texels": sigma,
                  "confidence_percentiles_1_10_50_90_99": np.percentile(confidence, [1, 10, 50, 90, 99]).tolist(),
                  "confidence_mean": float(confidence.mean()),
                  "use": "Decode after linear filtering; multiply anisotropy by B and preferably filtered RG vector length when distant. BrushRotation adds an explicit global rotation."})
    record["maps"]["Direction"] = entry
    # The authored NormalDX's XY are dominated by a common variation, so it does
    # not supply a usable local brushing orientation. Preserve it and derive a
    # physically coherent normal from the same authentic height used above.
    record["original_normal"] = record["maps"]["Normal"]
    scale = 0.03
    normal = np.stack([-nx * w * scale, -ny * h * scale, np.ones_like(height)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    data = encode_png(np.rint(np.clip(normal * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8))
    path = output / "aluminum/Maps/NormalFromHeight.png"
    store_immutable(path, data)
    entry = image_record(data, "Normal")
    entry.update({"path": path.relative_to(output).as_posix(),
                  "source_sha256": record["maps"]["Height"]["sha256"],
                  "modifications": "Periodic central differences in U/V of normalized16-bit source Height, divided by2*texel; N=normalize(-dHdu*.03,-dHdv*.03,1). Encoded DirectX8-bit tangent space. Both XY gradient signs agree with upstream Tile/Oak/Leather NormalDX-height correlations below-.89.",
                  "tile_relative_height_scale": scale,
                  "limitation": "Scale .03 is an explicit chosen microrelief strength, not measured physical depth. Original NormalDX retained unchanged in original_normal."})
    record["maps"]["Normal"] = entry
    record["orientation_source_note"] = "Raw source NormalDX tensor gave ambiguous near-uniform -45deg orientation. Independent full16 Non-Color Blender decode found XY correlation .99924 and median decoded normal length .9035. Cause not established; no upstream defect claim. Runtime normal and Direction instead share authored Height. The initial normal-tensor map is retained as a candidate diagnostic."


def contact_sheet(output, materials):
    canvas = Image.new("RGB", (6 * 256, 6 * 286), (30, 30, 34))
    draw = ImageDraw.Draw(canvas)
    for column, (key, record) in enumerate(materials.items()):
        for row, channel in enumerate(["BaseColor", "Normal", "Roughness", "Height", "Direction", "Mask"]):
            if channel not in record["maps"]:
                continue
            image = Image.open(output / record["maps"][channel]["path"])
            if image.mode in {"I", "I;16"}:
                image = Image.fromarray(np.rint(np.asarray(image, dtype=float) / 257).astype(np.uint8))
            image = image.convert("RGB").resize((256, 256), Image.Resampling.LANCZOS)
            x, y = column * 256, row * 286
            canvas.paste(image, (x, y + 25))
            draw.text((x + 5, y + 5), key + " / " + channel, fill="white")
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", compress_level=9)
    store_immutable(output / "FinalSourceMapContactSheet.png", buffer.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = output / "Manifest.json"
    pins = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    license_path = output / "License" / "ambientCG-license.html"
    license_data = license_path.read_bytes() if license_path.exists() else fetch(LICENSE_URL)
    if b"CC0" not in license_data or b"Creative Commons" not in license_data:
        raise RuntimeError("Official license page did not contain expected CC0 statement")
    store_immutable(license_path, license_data)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda key: source_material(key, output, pins), SELECTION))
    materials = dict(results)
    derive_tile_mask(output, materials)
    derive_aluminum_direction(output, materials)
    contact_sheet(output, materials)
    poly_license_path = output / "License/PolyHaven-license.html"
    poly_license = poly_license_path.read_bytes() if poly_license_path.exists() else fetch("https://polyhaven.com/license")
    if b"CC0" not in poly_license:
        raise RuntimeError("Official Poly Haven license did not contain CC0 statement")
    store_immutable(poly_license_path, poly_license)
    manifest = {"schema_version": 1, "retrieved_utc": pins["retrieved_utc"] if pins else datetime.now(timezone.utc).isoformat(),
                "license": {"spdx": "CC0-1.0", "url": LICENSE_URL, "snapshot": license_path.relative_to(output).as_posix(),
                            "sha256": digest(license_data), "terms": "Raw downloadable assets may be copied, modified and redistributed, including commercially; attribution is optional."},
                "generator_source": "Tools/UsfMaterials/source_batch1_textures.py",
                "generator_sha256": digest(Path(__file__).read_bytes()),
                "additional_licenses": [{"spdx": "CC0-1.0", "url": "https://polyhaven.com/license", "snapshot": poly_license_path.relative_to(output).as_posix(), "sha256": digest(poly_license)}],
                "materials": materials, "validation": "Source ZIP CRCs, required maps, dimensions, exact source-map hashes and boundary-neighbor steps. No runtime import, shading or artistic acceptance is claimed."}
    store_immutable(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps({key: {"asset": value["asset_id"], "channels": list(value["maps"])} for key, value in materials.items()}, indent=2))


if __name__ == "__main__":
    main()
