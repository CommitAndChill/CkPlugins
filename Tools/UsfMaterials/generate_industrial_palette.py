"""Generate owned, seamless linear data textures for the industrial surface family.

Requires NumPy and Pillow. No downloads or Unreal dependencies. Run from any cwd:
    python Tools/UsfMaterials/generate_industrial_palette.py
Existing output is only replaced when byte-identical; use a new --output directory
when revising this generator. This keeps published source receipts immutable.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


SEED = 731905
REVISION = 1
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "Plugins/CkTests/Resources/CkUsf/IndustrialPalette"


def periodic_field(size, seed, low, high, aspect=1.0):
    """Real, band-limited periodic random field, normalized to unit deviation.

    Integer Fourier modes guarantee f(u+1,v)=f(u,v+1)=f(u,v). Pixel centers
    cover [0,1) without duplicated border texels. No independent border repair.
    Elliptical frequency filtering permits directional machining/streaks.
    """
    rng = np.random.Generator(np.random.PCG64(seed))
    spectrum = np.fft.rfft2(rng.standard_normal((size, size)))
    fx = np.fft.rfftfreq(size) * size
    fy = np.fft.fftfreq(size)[:, None] * size
    radius = np.sqrt((fx[None, :] * aspect) ** 2 + fy**2)
    # Smooth compact support, with no content above the stated high frequency.
    t = np.clip((radius - low) / (high - low), 0.0, 1.0)
    envelope = np.sin(np.pi * t) ** 2
    envelope[(radius <= low) | (radius >= high)] = 0.0
    physical_radius = np.sqrt(fx[None, :] ** 2 + fy**2)
    envelope *= 1.0 - smoothstep(size * 0.09, size * 0.125, physical_radius)
    spectrum *= envelope
    field = np.fft.irfft2(spectrum, s=(size, size))
    return field / field.std()


def smoothstep(low, high, value):
    t = np.clip((value - low) / (high - low), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def bounded(value):
    return np.clip(value, 0.0, 1.0)


def fields():
    n = 1024
    steel = bounded(0.5 + 0.105 * periodic_field(n, SEED, 5, 118, 9)
                    + 0.035 * periodic_field(n, SEED + 1, 25, 130, 0.4))
    paint = bounded(0.5 + 0.125 * periodic_field(n, SEED + 2, 25, 112)
                    + 0.035 * periodic_field(n, SEED + 3, 8, 32))
    pits = smoothstep(0.25, 2.2, periodic_field(n, SEED + 4, 9, 66)
                      + 0.22 * periodic_field(n, SEED + 5, 45, 110))
    rust = bounded(0.68 - pits * 0.48
                   + 0.055 * periodic_field(n, SEED + 6, 20, 90))
    dust = bounded(0.5 + 0.11 * periodic_field(n, SEED + 7, 8, 65)
                   + 0.04 * periodic_field(n, SEED + 8, 50, 110))
    detail = np.stack([steel, paint, rust, dust], axis=-1)

    n = 256
    cluster = periodic_field(n, SEED + 10, 0, 7)
    breakup = periodic_field(n, SEED + 11, 5, 19)
    fine = periodic_field(n, SEED + 12, 17, 36)
    # Preserve soft values: shader coverage thresholds determine actual chips.
    chips = smoothstep(-1.9, 1.9, cluster + 0.45 * breakup + 0.15 * fine)
    oxidation = smoothstep(-2.0, 2.0, 0.65 * cluster
                            + 0.75 * periodic_field(n, SEED + 13, 1, 11)
                            + 0.2 * fine)
    streaks = periodic_field(n, SEED + 14, 0.5, 5, 0.12)
    grime = smoothstep(-1.8, 2.0, 0.75 * streaks
                       + 0.4 * periodic_field(n, SEED + 15, 0, 6))
    macro = bounded(0.5 + 0.16 * periodic_field(n, SEED + 16, 0, 5)
                    + 0.045 * periodic_field(n, SEED + 17, 3, 10))
    placement = np.stack([chips, oxidation, grime, macro], axis=-1)
    return detail, placement


def png_bytes(pixels):
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def channel_stats(pixels, names):
    result = {}
    for i, name in enumerate(names):
        values = pixels[:, :, i].astype(np.float64) / 255.0
        dx = np.abs(values - np.roll(values, 1, axis=1))
        dy = np.abs(values - np.roll(values, 1, axis=0))
        result[name] = {
            "min": float(values.min()), "max": float(values.max()),
            "mean": float(values.mean()), "stddev": float(values.std()),
            "percentiles_1_10_50_90_99": np.percentile(values, [1, 10, 50, 90, 99]).tolist(),
            "fraction_below_0_1": float((values < 0.1).mean()),
            "fraction_above_0_9": float((values > 0.9).mean()),
            "wrap_x_mean_step": float(dx[:, 0].mean()),
            "interior_x_mean_step": float(dx[:, 1:].mean()),
            "wrap_y_mean_step": float(dy[0, :].mean()),
            "interior_y_mean_step": float(dy[1:, :].mean()),
        }
    return result


def make_preview(detail, placement):
    canvas = Image.new("RGB", (1024, 600), (28, 28, 32))
    draw = ImageDraw.Draw(canvas)
    names = ["Steel height", "Paint peel height", "Rust pit height", "Dust",
             "Chips", "Oxidation", "Directional grime", "Macro discoloration"]
    for idx, name in enumerate(names):
        source = detail if idx < 4 else placement
        tile = Image.fromarray(source[:, :, idx % 4]).resize((256, 256), Image.Resampling.LANCZOS)
        x, y = (idx % 4) * 256, (idx // 4) * 300
        canvas.paste(tile.convert("RGB"), (x, y + 32))
        draw.text((x + 8, y + 8), name, fill=(235, 235, 235))
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    detail, placement = fields()
    detail = np.rint(bounded(detail) * 255).astype(np.uint8)
    placement = np.rint(bounded(placement) * 255).astype(np.uint8)
    images = {
        "IndustrialDetail_RGBA.png": png_bytes(detail),
        "IndustrialPlacement_RGBA.png": png_bytes(placement),
        "ChannelPreview.png": make_preview(detail, placement),
    }
    modes = np.arange(-130, 131, dtype=np.float64)
    periodic_error = float(np.abs(np.exp(2j * np.pi * modes) - 1.0).max())
    assert periodic_error < 1e-12
    receipt = {
        "schema": 1, "generator_revision": REVISION, "seed": SEED,
        "source": "Tools/UsfMaterials/generate_industrial_palette.py",
        "source_sha256": sha256(Path(__file__).read_bytes()),
        "provenance": "Original procedural fields generated by this repository script; no third-party image inputs or downloads.",
        "dependencies": {"numpy": np.__version__, "Pillow": Image.__version__},
        "algorithm": "PCG64-seeded Gaussian white noise, smooth compact-support integer Fourier bands, fixed height ranges and smoothstep placement composition. No per-image min/max normalization.",
        "color_space": "Linear data in unsigned 8-bit RGBA PNG; no sRGB, ICC or gamma metadata.",
        "detail": {
            "file": "IndustrialDetail_RGBA.png", "size": [1024, 1024],
            "channels": {"R": "steel machining height", "G": "paint orange peel height", "B": "rust pitting height (lower = deeper)", "A": "dust variation"},
            "band_limit": "Input modes smoothly taper to zero at 128 cycles/tile in every direction (at least 8 texels/cycle). Most channels <=112 cycles/tile. No single-texel impulses.",
            "statistics": channel_stats(detail, ["R", "G", "B", "A"]),
        },
        "placement": {
            "file": "IndustrialPlacement_RGBA.png", "size": [256, 256],
            "channels": {"R": "clustered chip field with nested breakup", "G": "oxidation field", "B": "directional grime/streak field (streaks run V)", "A": "macro discoloration"},
            "band_limit": "All input modes smoothly taper to zero at 32 cycles/tile in every direction (at least 8 texels/cycle). Smoothstep adds gentle harmonics. Use mips at distance.",
            "statistics": channel_stats(placement, ["R", "G", "B", "A"]),
        },
        "tiling_validation": {
            "construction": "Each field is an inverse FFT of integer modes on a unit torus. Pointwise sums/clamps/smoothsteps preserve periodicity. Quantization is pointwise. Adjacent edge texels are neighbors, intentionally not duplicates.",
            "max_integer_mode_unit_period_basis_error": periodic_error,
            "edge_check": "Per-channel wrap steps and interior steps reported above; equality of first/last texels is not required for seamless sampling.",
        },
        "unreal_import": {
            "sRGB": False, "compression": "TC_Masks", "compress_without_alpha": False,
            "address_x": "Wrap", "address_y": "Wrap", "filter": "Default (trilinear/anisotropic via texture group)",
            "mip_generation": "TMGS_SimpleAverage", "lod_group": "TEXTUREGROUP_World",
            "sampler_type": "Masks", "use": "Sample detail and placement at independent scales. Decode heights as linear scalars; these are not normal maps. Derive restrained tangent detail normals in the pixel shader; fade undersampled detail and retain mips.",
            "limitation": "Packed mask block compression may alter heights; compare TC_Masks versus uncompressed RGBA8 in Unreal if gradient artifacts appear. No runtime import or rendered-quality claim accompanies these sources.",
        },
        "outputs": {name: {"sha256": sha256(data), "bytes": len(data)} for name, data in images.items()},
    }
    images["SourceReceipt.json"] = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    # Check the entire batch before creating/replacing files.
    for name, data in images.items():
        path = args.output / name
        if path.exists() and path.read_bytes() != data:
            raise SystemExit(f"Refusing to overwrite changed immutable source: {path}. Choose a new --output directory.")
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in images.items():
        path = args.output / name
        if not path.exists():
            path.write_bytes(data)
        print(f"{name}: {len(data)} bytes SHA256 {sha256(data)}")
    print(f"Integer Fourier periodicity basis error: {periodic_error:.3e}")


if __name__ == "__main__":
    main()
