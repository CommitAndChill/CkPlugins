"""Source the approved second CC0 material batch without importing into Unreal.

Requires Pillow and NumPy. Run from any cwd. Existing receipts pin subsequent
runs, and byte-different sources/outputs are rejected rather than overwritten.
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
DEFAULT = ROOT / "Plugins/CkTests/Resources/CkUsf/Batch2Textures"
SELECTION = {
    "canvas": ("LibraryCanvas", "polyhaven", "stretch_poplin",
               "Cotton plain weave: actual stretch poplin source, not heavy canvas. The stable look ID is LibraryCanvas; present it as Cotton plain weave."),
    "suede": ("LibrarySuede", "ambientcg", "Leather039",
              "Actual fine light suede source; no invented leather pebbling or wear overlay."),
    "terracotta": ("LibraryTerracotta", "polyhaven", "brown_floor_tiles",
                   "Actual terracotta floor tiles, intact grid with subtle source wear. No claim that these are pristine or unglazed; no added aging."),
    "marble": ("LibraryMarble", "ambientcg", "Marble012",
               "Actual polished white/gray veined marble source, with source-authored surface variation."),
    "rubber": ("LibraryRubber", "ambientcg", "Rubber004",
               "Actual fine-grain rubber gym-floor source reused as a dense hard-rubber finish. Source does not establish molding process or measured mechanical hardness."),
    "glass": ("LibraryGlass", "ambientcg", "Smear005",
              "Authored surface-imperfection smear Normal and Opacity, not a clean optical glass scan. Optional subtle handling finish only; no grime color or transmission mask by default."),
}
AMBIENT_SUFFIX = {"BaseColor": "Color", "Normal": "NormalDX", "Roughness": "Roughness", "Height": "Displacement", "AO": "AmbientOcclusion", "Opacity": "Opacity"}
POLY_SUFFIX = {"BaseColor": "Diffuse", "Normal": "nor_dx", "Roughness": "Rough", "Height": "Displacement", "AO": "AO"}
HOSTS = {"ambientcg.com", "docs.ambientcg.com", "acg-download.struffelproductions.com", "polyhaven.com", "api.polyhaven.com", "dl.polyhaven.org"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def immutable(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError("Refusing changed owned source/output: " + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def fetch(url, max_bytes=32_000_000):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS:
        raise RuntimeError("Unexpected source URL: " + url)
    request = urllib.request.Request(url, headers={"User-Agent": "CkMaterialLibrary/1.0 (CC0 texture source evaluation)"})
    with urllib.request.urlopen(request, timeout=90) as response:
        if urllib.parse.urlparse(response.url).hostname not in HOSTS:
            raise RuntimeError("Unexpected source redirect")
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise RuntimeError("Source exceeds focused download limit: " + url)
        return data


def cached(path, url):
    data = path.read_bytes() if path.exists() else fetch(url)
    immutable(path, data)
    return data


def image_info(data, channel, relative, look):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Expected a PNG map: " + relative)
    image = Image.open(io.BytesIO(data))
    image.load()
    original_mode = image.mode
    if image.mode == "P":
        image = image.convert("RGB")
    array = np.asarray(image)
    bit_depth = data[24]
    divisor = 65535.0 if bit_depth == 16 and array.dtype.itemsize > 1 else 255.0
    values = array.astype(np.float64) / divisor
    if not np.isfinite(values).all() or min(image.size) < 256 or max(image.size) > 2048:
        raise RuntimeError("Invalid or unexpectedly sized source map: " + relative)
    entry = {
        "path": relative, "sha256": sha256(data), "bytes": len(data),
        "width": image.width, "height": image.height, "mode": image.mode,
        "source_mode": original_mode, "bit_depth": bit_depth,
        "decoded_dtype": str(array.dtype), "statistics_divisor": divisor,
        "statistics_precision_note": "Pillow decodes RGB16 PNGs as RGB8; grayscale16 remains16-bit. Statistics describe decoded pixels, not original RGB16 precision.",
        "color_space": "sRGB" if channel == "BaseColor" else "linear",
        "normal_convention": "DirectX tangent space; do not flip green" if channel == "Normal" else None,
        "runtime_name": "T_" + look + "_" + channel,
        "channel_mean": np.atleast_1d(values.mean(axis=(0, 1))).tolist(),
        "channel_stddev": np.atleast_1d(values.std(axis=(0, 1))).tolist(),
        "range": [float(values.min()), float(values.max())],
        "wrap_step_mean": {"x": float(np.abs(values[:, 0] - values[:, -1]).mean()), "y": float(np.abs(values[0] - values[-1]).mean())},
        "interior_step_mean": {"x": float(np.abs(np.diff(values, axis=1)).mean()), "y": float(np.abs(np.diff(values, axis=0)).mean())},
        "import_settings": {
            "sRGB": channel == "BaseColor", "compression": "TC_Normalmap" if channel == "Normal" else ("TC_Default" if channel == "BaseColor" else "TC_Masks"),
            "flip_green_channel": False, "address_x": "Wrap", "address_y": "Wrap", "mips": "TMGS_SimpleAverage",
            "npot_note": "Preserve original sources. Explicitly resize runtime import to1024 square if NPOT mips/streaming require it; retain original physical coverage separately." if image.width & (image.width - 1) or image.height & (image.height - 1) else None,
        },
    }
    if channel == "Normal":
        if values.ndim != 3 or values.shape[2] < 3:
            raise RuntimeError("Normal must contain RGB vectors")
        lengths = np.linalg.norm(values[:, :, :3] * 2 - 1, axis=-1)
        entry["decoded_normal_length_percentiles_1_50_99"] = np.percentile(lengths, [1, 50, 99]).tolist()
    return entry


def save_map(output, key, look, channel, data, origin):
    path = output / key / "Maps" / (channel + ".png")
    immutable(path, data)
    entry = image_info(data, channel, path.relative_to(output).as_posix(), look)
    entry.update(origin)
    return entry


def ambient_source(output, key, look, aid, pins):
    api_url = "https://ambientcg.com/api/v2/full_json?" + urllib.parse.urlencode({"id": aid, "include": "tagData,displayData,downloadData,dimensionsData"})
    metadata = output / "Metadata" / (aid + ".json")
    raw = cached(metadata, api_url)
    assets = json.loads(raw)["foundAssets"]
    if len(assets) != 1 or assets[0]["assetId"] != aid:
        raise RuntimeError("Expected exactly selected ambientCG asset: " + aid)
    asset = assets[0]
    descriptor = next(x for x in asset["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"] if x["attribute"] == "1K-PNG")
    candidate = output / "Candidates" / descriptor["fileName"]
    archive_path = candidate if candidate.exists() else output / "Archives" / descriptor["fileName"]
    archive = cached(archive_path, descriptor["downloadLink"])
    if len(archive) != descriptor["size"]:
        raise RuntimeError("Official archive size mismatch: " + aid)
    if pins and pins["materials"][key]["archive"]["sha256"] != sha256(archive):
        raise RuntimeError("Pinned archive hash mismatch: " + aid)
    result = {
        "source_url": "https://ambientcg.com/a/" + aid,
        "metadata_path": metadata.relative_to(output).as_posix(), "metadata_sha256": sha256(raw),
        "author": "ambientCG / Lennart Demes (publisher; no individual author field)", "author_source": "https://docs.ambientcg.com/legal/",
        "creation_method": asset["creationMethod"], "release_date": asset["releaseDate"], "official_tags": asset["tags"],
        "coverage_cm": {axis: asset.get("dimension" + axis.upper()) for axis in "xyz"},
        "coverage_note": "Zero means not specified by publisher; no inferred physical scale.",
        "archive": {"path": archive_path.relative_to(output).as_posix(), "sha256": sha256(archive), "url": descriptor["downloadLink"], "bytes": len(archive)}, "maps": {},
    }
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        if zipped.testzip() is not None:
            raise RuntimeError("Archive CRC failure: " + aid)
        for channel, suffix in AMBIENT_SUFFIX.items():
            member = aid + "_1K-PNG_" + suffix + ".png"
            if member not in zipped.namelist():
                continue
            if key == "glass" and channel not in {"Normal", "Opacity"}:
                continue
            data = zipped.read(member)
            origin = {"archive_member": member, "modifications": "None; byte-identical publisher PNG"}
            result["maps"][channel] = save_map(output, key, look, channel, data, origin)
        if key == "glass":
            # This is a real authored concentration mask, not fabricated noise or
            # claimed calibrated roughness. Shader defaults perform the finish remap.
            opacity = result["maps"]["Opacity"]
            data = (output / opacity["path"]).read_bytes()
            result["maps"]["Roughness"] = save_map(output, key, look, "Roughness", data, {
                "archive_member": opacity["archive_member"],
                "modifications": "Byte-identical source Opacity, repurposed as a roughness-variation input only; not a measured roughness map.",
                "source_sha256": opacity["sha256"], "shader_decode": "roughness = 0.045 + 0.035 * sample.r (do not remap twice)",
                "default_normal_strength": 0.04,
            })
            result["maps"]["Opacity"]["usage"] = "Optional finish concentration only; do not drive optical transmission or visible grime color by default."
    return result


def poly_source(output, key, look, aid, pins):
    info_path, files_path = output / "Metadata" / (aid + "_info.json"), output / "Metadata" / (aid + "_files.json")
    info_data = cached(info_path, "https://api.polyhaven.com/info/" + aid)
    files_data = cached(files_path, "https://api.polyhaven.com/files/" + aid)
    info, files = json.loads(info_data), json.loads(files_data)
    result = {
        "source_url": "https://polyhaven.com/a/" + aid, "author": info["authors"], "official_tags": info["tags"],
        "description": info["description"], "release_date_unix": info["date_published"],
        "metadata_path": info_path.relative_to(output).as_posix(), "metadata_sha256": sha256(info_data),
        "files_metadata_path": files_path.relative_to(output).as_posix(), "files_metadata_sha256": sha256(files_data),
        "coverage_cm": {"x": info["dimensions"][0] / 10, "y": info["dimensions"][1] / 10},
        "coverage_note": "Official millimeter dimensions converted to centimeters; original pixel aspect is retained.",
        "originals": {}, "maps": {},
    }
    for channel, upstream in POLY_SUFFIX.items():
        if upstream not in files or "png" not in files[upstream].get("1k", {}):
            continue
        descriptor = files[upstream]["1k"]["png"]
        filename = descriptor["url"].rsplit("/", 1)[1]
        candidate = output / "Candidates" / filename
        original = candidate if candidate.exists() else output / key / "Original" / filename
        data = cached(original, descriptor["url"])
        if len(data) != descriptor["size"] or hashlib.md5(data).hexdigest() != descriptor["md5"]:
            raise RuntimeError("Official Poly Haven integrity mismatch: " + filename)
        result["originals"][channel] = {"path": original.relative_to(output).as_posix(), "sha256": sha256(data), "url": descriptor["url"], "upstream_md5": descriptor["md5"]}
        result["maps"][channel] = save_map(output, key, look, channel, data, {
            "source_url": descriptor["url"], "modifications": "None; byte-identical1K publisher PNG, no resampling or new grain",
        })
    return result


def source_one(item, output, pins):
    key, (look, provider, aid, notes) = item
    result = ambient_source(output, key, look, aid, pins) if provider == "ambientcg" else poly_source(output, key, look, aid, pins)
    required = {"Normal", "Roughness"} if key == "glass" else {"BaseColor", "Normal", "Roughness"}
    if not required.issubset(result["maps"]):
        raise RuntimeError("Missing required source maps: " + key)
    result.update({"look_id": look, "asset_id": aid, "provider": provider, "license": "CC0-1.0", "identity_notes": notes})
    return key, result


def contact_sheet(output, materials):
    canvas = Image.new("RGB", (1536, 4 * 286), (30, 30, 34))
    draw = ImageDraw.Draw(canvas)
    for column, key in enumerate(SELECTION):
        for row, channel in enumerate(["BaseColor", "Normal", "Roughness", "Opacity"]):
            x, y = column * 256, row * 286
            draw.text((x + 5, y + 5), key + " / " + channel, fill="white")
            if channel not in materials[key]["maps"]:
                draw.text((x + 5, y + 60), "Not used / not fabricated", fill=(160, 160, 160))
                continue
            image = Image.open(output / materials[key]["maps"][channel]["path"])
            if image.mode in {"I", "I;16", "I;16B", "I;16L"}:
                image = Image.fromarray(np.rint(np.asarray(image, dtype=np.float64) / 257).astype(np.uint8))
            image = image.convert("RGB").resize((256, 256), Image.Resampling.LANCZOS)
            canvas.paste(image, (x, y + 25))
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", compress_level=9)
    immutable(output / "SourceMapContactSheet.png", buffer.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = output / "Manifest.json"
    pins = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    licenses = []
    for provider, url in [("ambientcg", "https://docs.ambientcg.com/license/"), ("polyhaven", "https://polyhaven.com/license")]:
        path = output / "License" / (provider + ".html")
        data = cached(path, url)
        if b"CC0" not in data:
            raise RuntimeError("Official license snapshot lacks expected CC0 statement")
        licenses.append({"provider": provider, "spdx": "CC0-1.0", "url": url, "path": path.relative_to(output).as_posix(), "sha256": sha256(data)})
    with ThreadPoolExecutor(max_workers=3) as pool:
        materials = dict(pool.map(lambda item: source_one(item, output, pins), SELECTION.items()))
    contact_sheet(output, materials)
    manifest = {
        "schema_version": 1, "retrieved_utc": pins["retrieved_utc"] if pins else datetime.now(timezone.utc).isoformat(),
        "generator_source": "Tools/UsfMaterials/source_batch2_textures.py", "generator_sha256": sha256(Path(__file__).read_bytes()),
        "maps_root": "Plugins/CkTests/Resources/CkUsf/Batch2Textures", "licenses": licenses, "materials": materials,
        "verification_scope": "Official source metadata/license snapshots;1K source dimensions, ZIP CRC or upstream MD5, SHA256 pins, channel distributions, boundary-neighbor steps, actual source-map contact sheet. No rendering, optical calibration, import, or artistic acceptance is claimed.",
        "known_source_gaps": "Cotton is actual stretch poplin rather than heavy canvas. Rubber originates in fine-grain flooring rather than certified molded rubber. Glass uses authored optional smear finish, not an optical glass scan; its canonical Roughness is an explicit variation mask. Terracotta includes slight existing source wear, no extra aging.",
    }
    immutable(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps({key: {"asset": record["asset_id"], "look_id": record["look_id"], "maps": {ch: [e["width"], e["height"]] for ch, e in record["maps"].items()}} for key, record in materials.items()}, indent=2))
    print("Manifest SHA256", sha256(manifest_path.read_bytes()))


if __name__ == "__main__":
    main()
