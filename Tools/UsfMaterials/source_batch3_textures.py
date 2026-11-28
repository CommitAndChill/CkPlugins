"""Source the approved third CC0 material batch; no Unreal or manifest mutation.

Requires sibling source_batch2_textures.py, NumPy and Pillow. Reuses that script's
checked download, source-archive and image-contract helpers. Cached receipts pin
subsequent runs. Original source images are retained without alteration.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys

# Importing shared host helpers must not write files into their directory.
sys.dont_write_bytecode = True
import source_batch2_textures as source


ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "Plugins/CkTests/Resources/CkUsf/Batch3Textures"
SELECTION = {
    "velvet": ("LibraryVelvet", "polyhaven", "velour_velvet",
               "Actual napped velour velvet textile, not the silk source. Surface-only texture cannot reproduce geometric pile silhouette by itself."),
    "walnut": ("LibraryWalnut", "polyhaven", "walnut_veneer_02",
               "Actual clean walnut veneer, no added aging. Any finished coating is independently authored by the material."),
    "granite": ("LibraryGranite", "ambientcg", "Granite002A",
                "Actual intact countertop granite source with aligned mineral color and surface response."),
    "brass": ("LibraryBrass", "ambientcg", "Metal009",
              "Brushed STEEL machining data reused with independently authored BRASS reflectance. Source is not a brass scan. Source BaseColor serves only low-amplitude grain variation after shader normalization; brass F0 is authored independently near(.95,.64,.23)."),
    "frosted_glass": ("LibraryFrostedGlass", "ambientcg", "Plastic010",
                      "Clean smooth plastic finish Normal/Roughness reused as a fine matte glass-etch finish. Not an optical glass scan, no smudge overlay. Source BaseColor is retained as provenance, not glass tint or transmission. Texture data does not establish a particular renderer's rough-refraction or background-blur capability."),
    "carbon_fiber": ("LibraryCarbonFiber", "ambientcg", "Fabric004",
                     "Official clean carbon/fiber-tagged authored crossed-tow weave, despite upstream Fabric category. BC/Normal/Roughness share actual weave layout; resin is independently authored with native ClearCoat. Carbon stays dielectric with Metallic0; source Metalness is intentionally excluded."),
}


def sheet(output, materials, detail=False):
    canvas = source.Image.new("RGB", (1536, 3 * 286), (30, 30, 34))
    draw = source.ImageDraw.Draw(canvas)
    for column, key in enumerate(SELECTION):
        for row, channel in enumerate(["BaseColor", "Normal", "Roughness"]):
            entry = materials[key]["maps"][channel]
            image = source.Image.open(output / entry["path"])
            if detail:
                w, h = image.size
                image = image.crop((w // 2 - 64, h // 2 - 64, w // 2 + 64, h // 2 + 64))
            if image.mode in {"I", "I;16", "I;16B", "I;16L"}:
                image = source.Image.fromarray(source.np.rint(source.np.asarray(image, dtype=float) / 257).astype(source.np.uint8))
            filter_mode = source.Image.Resampling.NEAREST if detail else source.Image.Resampling.LANCZOS
            image = image.convert("RGB").resize((256, 256), filter_mode)
            x, y = column * 256, row * 286
            canvas.paste(image, (x, y + 25))
            draw.text((x + 5, y + 5), key + " / " + channel + (" crop x2" if detail else ""), fill="white")
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", compress_level=9)
    source.immutable(output / ("SourceDetailContactSheet.png" if detail else "SourceMapContactSheet.png"), buffer.getvalue())


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
        data = source.cached(path, url)
        if b"CC0" not in data:
            raise RuntimeError("Official source license lacks expected CC0 statement")
        licenses.append({"provider": provider, "spdx": "CC0-1.0", "url": url,
                         "path": path.relative_to(output).as_posix(), "sha256": source.sha256(data)})
    with ThreadPoolExecutor(max_workers=3) as pool:
        materials = dict(pool.map(lambda item: source.source_one(item, output, pins), SELECTION.items()))
    materials["carbon_fiber"]["excluded_channel"] = {
        "name": "Metalness", "archive_member": "Fabric004_1K-PNG_Metalness.png",
        "reason": "Upstream1-bit source Metalness is all true. It is retained inside the source ZIP but intentionally neither extracted for runtime nor consumed; carbon material Metallic must remain0.",
    }
    materials["carbon_fiber"]["direction_note"] = "No invented direction or procedural weave grid. Current shader consumes the actual BC/Normal/Roughness weave; dedicated direction extraction is not required by its native ClearCoat contract."
    materials["frosted_glass"]["finish_contract"] = "Use actual fine microtexture Normal/Roughness at restrained strength; do not use source plastic color or claim physically blurred transmission from texture sampling alone."
    sheet(output, materials)
    sheet(output, materials, detail=True)
    helper_path = Path(source.__file__).resolve()
    manifest = {
        "schema_version": 1, "retrieved_utc": pins["retrieved_utc"] if pins else datetime.now(timezone.utc).isoformat(),
        "generator_source": "Tools/UsfMaterials/source_batch3_textures.py", "generator_sha256": source.sha256(Path(__file__).read_bytes()),
        "required_helper": helper_path.relative_to(ROOT).as_posix(), "required_helper_sha256": source.sha256(helper_path.read_bytes()),
        "maps_root": "Plugins/CkTests/Resources/CkUsf/Batch3Textures", "licenses": licenses, "materials": materials,
        "verification_scope": "Source ZIP CRC or publisher MD5, SHA256 pins, real image dimensions and data/color contracts, decoded channel statistics and boundary steps. Actual source overview/detail sheets. No editor import, rendering, optical calibration or artistic acceptance is claimed.",
        "known_source_reuse": "Brass uses steel machining finish under independently authored brass reflectance. Frosted glass uses actual clean plastic matte microfinish data, not an optical glass scan. Carbon source metallic map is intentionally excluded; native resin coat is a separate material response.",
    }
    source.immutable(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps({key: {"asset": value["asset_id"], "look_id": value["look_id"],
                           "maps": {channel: [entry["width"], entry["height"]] for channel, entry in value["maps"].items()}}
                      for key, value in materials.items()}, indent=2))
    print("Manifest SHA256", source.sha256(manifest_path.read_bytes()))


if __name__ == "__main__":
    main()
