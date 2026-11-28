"""Prepare the bounded linear aluminum recipe from pinned, existing CC0 sources.

Run: python Tools/UsfMaterials/source_linear_aluminum.py
No network, Unreal import, source-map mutation, or main-manifest edits.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "Plugins/CkTests/Resources/CkUsf/Batch1Textures"
OUTPUT = SOURCES / "AluminumLinear_v2"
PINS = {
    "BaseColor": ("aluminum/Maps/BaseColor.png", "4fba4ba6bdd8661ed989bb7d0877e16ee76c671e55729651011e0687cd8387b5"),
    "Normal": ("Candidates/Metal009_NormalDX.png", "1c007ae655e5c877ba2f92e0fe62eace193f46a56f3f6054cab25cb4bef86df4"),
    "Roughness": ("Candidates/Metal009_Roughness.png", "d3307a704f1708d6643c263983469827ea13818ba366083c4e93a1cec27c7317"),
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def describe(data, channel, path, size, runtime_name):
    image = Image.open(io.BytesIO(data))
    image.load()
    if image.size != size:
        raise RuntimeError("Unexpected image dimensions: " + path)
    return {
        "path": path, "sha256": sha256(data), "bytes": len(data),
        "width": image.width, "height": image.height,
        "mode": image.mode, "bit_depth": data[24],
        "color_space": "sRGB" if channel == "BaseColor" else "linear",
        "normal_convention": "DirectX tangent space; do not flip green" if channel == "Normal" else None,
        "runtime_name": runtime_name,
        "import_settings": {
            "sRGB": channel == "BaseColor",
            "compression": "TC_Normalmap" if channel == "Normal" else ("TC_Default" if channel == "BaseColor" else "TC_Masks"),
            "flip_green_channel": False, "address_x": "Wrap", "address_y": "Wrap",
            "mips": "TMGS_SimpleAverage",
        },
    }


def main():
    maps = {}
    for channel, (relative, expected) in PINS.items():
        data = (SOURCES / relative).read_bytes()
        if sha256(data) != expected:
            raise RuntimeError("Pinned source hash mismatch: " + relative)
        runtime = "T_LibraryAluminum_BaseColor" if channel == "BaseColor" else "T_LibraryAluminumLinear_" + channel
        maps[channel] = describe(data, channel, relative, (1024, 1024), runtime)
        maps[channel]["modifications"] = "None; existing upstream source file referenced without copying or alteration"
        maps[channel]["source_asset_id"] = "Metal051A" if channel == "BaseColor" else "Metal009"

    # A minimal block-sized power-of-two image keeps this analytical field constant
    # through every mip. RGB8 quantization of the ideal (1,.5,1) is explicit.
    image = Image.new("RGB", (4, 4), (255, 128, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=9)
    direction = buffer.getvalue()
    entry = describe(direction, "Direction", "AluminumLinear_v2/Direction.png", (4, 4), "T_LibraryAluminumLinear_Direction")
    entry.update({
        "packing": "RGB=(255,128,255): R=(1+cos(2theta))/2, G=(1+sin(2theta))/2, B=confidence1; ideal theta=0 radians, horizontal U-axis brushing",
        "decode": "theta=.5*atan2(2*G-1,2*R-1); theta is axial, modulo pi",
        "quantization_note": "RGB8 cannot encode .5 exactly; G128 gives decoded angle about .1123 degrees. This is the requested constant encoding, not spatial variation.",
        "modifications": "Analytical constant field only; no invented machining grain or source alteration",
    })
    maps["Direction"] = entry
    receipt = {
        "schema_version": 1, "recipe_id": "AluminumLinear_v2", "look_id": "LibraryAluminum",
        "generator_source": "Tools/UsfMaterials/source_linear_aluminum.py",
        "generator_sha256": sha256(Path(__file__).read_bytes()),
        "maps_root": "Plugins/CkTests/Resources/CkUsf/Batch1Textures",
        "license": {"spdx": "CC0-1.0", "official_url": "https://docs.ambientcg.com/license/",
                    "retained_snapshot": "License/ambientCG-license.html"},
        "sources": {
            "Metal009": {"url": "https://ambientcg.com/a/Metal009",
                         "api_url": "https://ambientcg.com/api/v2/full_json?id=Metal009&include=tagData,displayData,downloadData",
                         "author": "ambientCG / Lennart Demes", "identity": "Brushed steel; procedural PBR source, not aluminum",
                         "usage": "Only existing linear machining NormalDX and Roughness are reused; no steel source BaseColor is used."},
            "Metal051A": {"url": "https://ambientcg.com/a/Metal051A",
                          "author": "ambientCG / Lennart Demes",
                          "usage": "Existing aluminum BaseColor remains unchanged. Circular normal, height, and direction maps are excluded from this recipe."},
        },
        "identity_statement": "Machining data originates from authored brushed STEEL Metal009; the game material independently authors ALUMINUM reflectance. This is a reusable surface-finish recipe, not a scanned linear-brushed aluminum asset or proof of physical equivalence between alloys.",
        "direction_alignment": "Metal009 maps have parallel horizontal brush marks (U axis); a constant axial tangent replaces circular cell orientation.",
        "maps": maps,
        "verification_scope": "Pinned source hashes, decoded image dimensions, deterministic constant direction and receipt. No Unreal import, compilation, rendering, or artistic acceptance is claimed.",
    }
    outputs = {
        OUTPUT / "Direction.png": direction,
        OUTPUT / "Receipt.json": (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(),
    }
    # Preflight the complete batch before creating any outputs.
    for path, data in outputs.items():
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError("Refusing changed recipe output: " + str(path))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path, data in outputs.items():
        if not path.exists():
            path.write_bytes(data)
        print(path.relative_to(ROOT).as_posix(), "SHA256", sha256(data))
    print("Three pinned source maps verified; two deterministic outputs ready.")


if __name__ == "__main__":
    main()
