"""Create immutable BC8 derivatives and provenance for four source-backed native looks.

Run on the host. Only AdvancedBsdfV1 outputs are writable. Exact original PNG16
unfiltering is reused from derive_pebble_runtime_color.decode16; no gamma/grade/resize.
"""
from pathlib import Path
import hashlib
import io
import json
import sys
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image, PngImagePlugin
from derive_pebble_runtime_color import decode16
from advanced_bsdf_settings import LOOKS, TEXTURE_PARAMETERS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Plugins/CkTests/Resources/CkUsf/AdvancedBsdfV1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def immutable(path, data):
    if not path.resolve().is_relative_to(OUTPUT.resolve()):
        raise RuntimeError("Output escaped AdvancedBsdfV1")
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError("Preserve differing immutable output: " + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def main():
    evidence = {}
    pending = {}
    materials = {}
    for look, recipe in LOOKS.items():
        source_root = ROOT / "Plugins/CkTests/Resources/CkUsf" / recipe["source_batch"]
        original_manifest = source_root / "Manifest.json"
        manifest_data = original_manifest.read_bytes()
        manifest = json.loads(manifest_data)
        record = manifest["materials"][recipe["source_key"]]
        if record["license"] != "CC0-1.0":
            raise RuntimeError("Expected recorded CC0 source: " + look)
        receipt_path = "Evidence/" + recipe["source_batch"] + "-Manifest.json"
        pending[receipt_path] = manifest_data
        evidence[receipt_path] = {"path": receipt_path, "sha256": digest(manifest_data),
                                  "source_path": str(original_manifest.relative_to(ROOT)).replace("\\", "/")}
        for license_info in manifest["licenses"]:
            if license_info["provider"] != record["provider"]:
                continue
            data = (source_root / license_info["path"]).read_bytes()
            if digest(data) != license_info["sha256"]:
                raise RuntimeError("License receipt changed")
            path = "Evidence/" + recipe["source_batch"] + "-" + Path(license_info["path"]).name
            pending[path] = data
            evidence[path] = dict(license_info, path=path)
        for metadata_key in ["metadata_path", "files_metadata_path"]:
            if metadata_key not in record:
                continue
            data = (source_root / record[metadata_key]).read_bytes()
            hash_key = metadata_key.replace("_path", "_sha256")
            if digest(data) != record[hash_key]:
                raise RuntimeError("Official source metadata changed: " + look)
            path = "Evidence/" + look + "-" + Path(record[metadata_key]).name
            pending[path] = data
            evidence[path] = {"path": path, "sha256": digest(data)}
        item = {key: record[key] for key in ["asset_id", "provider", "author", "license", "source_url", "identity_notes"]}
        item.update(look_id=look, coverage_cm=record.get("coverage_cm"), source_manifest=receipt_path,
                    source_key=recipe["source_key"], maps={})
        for parameter, channel in TEXTURE_PARAMETERS:
            original = record["maps"][channel]
            path = (source_root / original["path"]).resolve()
            if not path.is_relative_to(source_root.resolve()):
                raise RuntimeError("Source map escaped its batch")
            data = path.read_bytes()
            if digest(data) != original["sha256"]:
                raise RuntimeError("Pinned original map changed: " + str(path))
            info = {key: original[key] for key in ["sha256", "width", "height", "bit_depth", "color_space"]}
            info.update(source_path=str(path.relative_to(ROOT)).replace("\\", "/"),
                        source_sha256=original["sha256"], normal_convention=original.get("normal_convention"),
                        runtime_asset="/CkFoundation/CkUsf/Textures/Library/T_" + recipe["runtime_basename"] + "_" + channel,
                        derived=False)
            if channel == "BaseColor" and original["bit_depth"] == 16:
                values, metadata = decode16(data)
                if values.shape[2] == 4 and not np.all(values[:, :, 3] == 65535):
                    raise RuntimeError("Unexpected source alpha: " + look)
                rgb = values[:, :, :3]
                q = ((rgb.astype(np.uint32) + 128) // 257).astype(np.uint8)
                error = np.abs(q.astype(np.float64) / 255 - rgb.astype(np.float64) / 65535)
                if error.max() > .5 / 255 + 1e-12:
                    raise RuntimeError("Encoded quantization bound exceeded")
                chunks = PngImagePlugin.PngInfo()
                for key, body in metadata.items():
                    chunks.add(key, body)
                buffer = io.BytesIO()
                Image.fromarray(q).save(buffer, format="PNG", compress_level=9, pnginfo=chunks)
                result = buffer.getvalue()
                if not np.array_equal(np.asarray(Image.open(io.BytesIO(result)).convert("RGB")), q):
                    raise RuntimeError("BC8 roundtrip changed encoded pixels")
                relative = look + "/Maps/BaseColor.png"
                pending[relative] = result
                info.update(path=relative, sha256=digest(result), bit_depth=8, derived=True,
                            runtime_asset="/CkFoundation/CkUsf/Textures/Native/T_" + look + "_BaseColor",
                            transform="q8=floor((q16+128)/257); no gamma transform, grade, resize or spatial change",
                            max_encoded_error=float(error.max()), mean_encoded_error=float(error.mean()),
                            retained_color_chunks={key.decode(): body.hex() for key, body in metadata.items()})
            info["runtime_resize_1024_square"] = bool(info["width"] & (info["width"] - 1) or info["height"] & (info["height"] - 1))
            item["maps"][channel] = info
        materials[look] = item
    result = {"schema_version": 1, "generator_source": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
              "generator_sha256": digest(Path(__file__).read_bytes()),
              "decoder_source": "Tools/UsfMaterials/derive_pebble_runtime_color.py",
              "decoder_sha256": digest((ROOT / "Tools/UsfMaterials/derive_pebble_runtime_color.py").read_bytes()),
              "provenance_evidence": list(evidence.values()), "materials": materials,
              "limits": "Source-backed authored BSDF presentation, not measured optical calibration. Original maps unchanged; BC8 only re-encodes existing encoded RGB. Velvet NPOT originals retained; runtime policy explicitly resizes all aligned maps to1024 square."}
    pending["Manifest.json"] = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    # Detect any conflicting prior output before writing even one file.
    for relative, data in pending.items():
        path = OUTPUT / relative
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError("Preserve differing immutable output: " + str(path))
    for relative, data in pending.items():
        immutable(OUTPUT / relative, data)
    print(json.dumps({"manifest": str((OUTPUT / "Manifest.json").relative_to(ROOT)),
                      "sha256": digest(pending["Manifest.json"]),
                      "derived_colors": {look: entry["maps"]["BaseColor"]["sha256"] for look, entry in materials.items() if entry["maps"]["BaseColor"]["derived"]}}, indent=2))


if __name__ == "__main__":
    main()
