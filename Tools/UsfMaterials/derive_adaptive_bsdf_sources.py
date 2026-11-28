"""Pin reused CC0 sources and author neutral, physical yarn-thickening utilities.

Only AdaptiveBsdfV1 outputs are writable. Slub height is a radius-profile model,
not inferred from albedo; BC is never replaced with procedural colored noise.
"""
from pathlib import Path
import hashlib
import io
import json
import sys
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Plugins/CkTests/Resources/CkUsf/AdaptiveBsdfV1"
SEED = 27241


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png(array):
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


def main():
    pending = {}
    materials = {}
    for name, batch, key in [("silk", "Batch1Textures", "silk"),
                             ("paint_surface", "Batch7Textures", "glossy_plastic"),
                             ("paint_metal", "Batch7Textures", "copper")]:
        root = ROOT / "Plugins/CkTests/Resources/CkUsf" / batch
        original = root / "Manifest.json"
        data = original.read_bytes()
        m = json.loads(data)
        record = m["materials"][key]
        if record["license"] != "CC0-1.0":
            raise RuntimeError("Expected retained CC0 source")
        pending["Evidence/" + batch + "-Manifest.json"] = data
        item = {field: record[field] for field in ["asset_id", "author", "license", "source_url", "identity_notes"]}
        item.update(source_batch=batch, source_key=key, manifest_sha256=sha(data), maps={})
        for channel, info in record["maps"].items():
            path = (root / info["path"]).resolve()
            if not path.is_relative_to(root.resolve()):
                raise RuntimeError("Source escaped its batch")
            if sha(path.read_bytes()) != info["sha256"]:
                raise RuntimeError("Retained source changed: " + str(path))
            item["maps"][channel] = dict(info, source_path=str(path.relative_to(ROOT)).replace("\\", "/"),
                                         runtime_name=info.get("runtime_name", "T_" + record["look_id"] + "_" + channel))
        for path in (root / "License").glob("*.html"):
            if batch == "Batch1Textures" and "polyhaven" not in path.name.lower():
                continue
            if batch == "Batch7Textures" and "ambientcg" not in path.name.lower():
                continue
            pending["Evidence/" + batch + "-" + path.name] = path.read_bytes()
        if record.get("metadata_path"):
            path = root / record["metadata_path"]
            if sha(path.read_bytes()) != record["metadata_sha256"]:
                raise RuntimeError("Official metadata changed")
            pending["Evidence/" + name + "-" + path.name] = path.read_bytes()
        materials[name] = item
    width, height = 1024, 1042
    width_cm, height_cm = 26.319942218838303, 26.78999900817871
    x = (np.arange(width, dtype=float) + .5) / width
    y = (np.arange(height, dtype=float) + .5) / height
    xx, yy = np.meshgrid(x, y)
    radius = np.zeros((height, width), dtype=float)
    rng = np.random.default_rng(SEED)
    # Ninety-six warp yarn lanes; finite elongated thickening events follow the yarn axis.
    # Randomness chooses yarn/position/extent, never substitutes a noise field for the textile.
    for index in range(72):
        lane = int(rng.integers(0, 96))
        center_x = (lane + .5) / 96
        center_y = float(rng.random())
        half_width_cm = float(rng.uniform(.025, .055))
        half_length_cm = float(rng.uniform(.65, 1.8))
        amplitude_cm = float(rng.uniform(.0025, .006))
        dx = np.abs(xx - center_x)
        dy = np.abs(yy - center_y)
        dx = np.minimum(dx, 1 - dx) * width_cm / half_width_cm
        dy = np.minimum(dy, 1 - dy) * height_cm / half_length_cm
        # A shallow rounded yarn cross-section with smooth finite shoulders and tapered ends.
        cross = np.maximum(1 - dx * dx, 0) ** 2
        longitudinal = np.maximum(1 - dy * dy, 0) ** 3
        radius += amplitude_cm * cross * longitudinal
    scale = float(radius.max())
    mask = radius / scale
    du = (np.roll(radius, -1, axis=1) - np.roll(radius, 1, axis=1)) / (2 * width_cm / width)
    dv = (np.roll(radius, -1, axis=0) - np.roll(radius, 1, axis=0)) / (2 * height_cm / height)
    normal = np.stack([-du, -dv, np.ones_like(radius)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    pending["Silk/SlubMask.png"] = png(np.round(mask * 255).astype(np.uint8))
    pending["Silk/SlubNormal.png"] = png(np.round((normal * .5 + .5) * 255).astype(np.uint8))
    pending["Silk/SlubHeight.png"] = png(np.round(mask * 65535).astype(np.uint16))
    utilities = {}
    for channel in ["SlubMask", "SlubNormal", "SlubHeight"]:
        path = "Silk/" + channel + ".png"
        utilities[channel] = {"path": path, "sha256": sha(pending[path]), "width": width, "height": height,
                              "bit_depth": 16 if channel == "SlubHeight" else 8, "color_space": "linear",
                              "normal_convention": "DirectX tangent space: decoded Nx=-dH/dU, Ny=-dH/dV" if channel == "SlubNormal" else None,
                              "runtime_name": "T_AdaptiveSlubSilk_" + channel}
    receipt = {"schema_version": 1, "generator_source": "Tools/UsfMaterials/derive_adaptive_bsdf_sources.py",
               "generator_sha256": sha(Path(__file__).read_bytes()), "materials": materials,
               "utilities": utilities, "authored_utility_license": "Original project-authored procedural radius-profile data; no external asset content in utility maps",
               "slub_model": {"seed": SEED, "events": 72, "warp_lanes": 96, "width_cm": width_cm, "height_cm": height_cm,
                 "height_range_cm": scale, "half_width_cm": [.025, .055], "half_length_cm": [.65, 1.8],
                 "event_radius_cm": [.0025, .006], "formula": "H=sum(radius*max(1-(dx/halfWidth)^2,0)^2*max(1-(dy/halfLength)^2,0)^3); periodic distances",
                 "normal_formula": "normalize(-centralDifferenceU(H),-centralDifferenceV(H),1); physical pixel spacing, same array orientation",
                 "nonzero_coverage": float(np.mean(mask > .01)), "mask_mean": float(mask.mean())},
               "evidence": [{"path": path, "sha256": sha(data)} for path, data in pending.items() if path.startswith("Evidence/")],
               "limits": "Independent authored slub reinterpretation on licensed crepe-satin backing; not a slub scan or Zorah source recreation. Paint microfinish reuses plastic/copper maps under authored dyed medium and neutral conductor; no scanned candy paint or metallic flake claim. All reused sources remain unchanged. Silk NPOT originals require recorded1024square runtime policy."}
    pending["Receipt-v2.json"] = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    for relative, data in pending.items():
        path = OUTPUT / relative
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError("Preserve differing immutable output: " + str(path))
    for relative, data in pending.items():
        path = OUTPUT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(data)
    print(json.dumps({"receipt_sha256": sha(pending["Receipt-v2.json"]), "utilities": utilities, "slub_model": receipt["slub_model"]}, indent=2))


if __name__ == "__main__":
    main()
