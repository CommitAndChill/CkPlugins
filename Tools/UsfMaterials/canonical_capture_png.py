"""Preserve PNG image bytes exactly while excluding bytes after the valid IEND.

Public canonical_png_bytes(data) is stdlib-only for future capture exporters.
CLI processes only captures pinned by the successful Adaptive rendered proof;
raw captures/proof are never changed. Derived outputs and receipt are immutable.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[2]
GALLERY = ROOT / "Saved/UsfMaterialGallery"
PROOF = GALLERY / "AdaptiveBsdf-RenderedProof.json"
DESTINATION = GALLERY / "AdaptiveCanonical"
RECEIPT = GALLERY / "AdaptiveBsdf-CanonicalCaptureReceipt.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def canonical_png_bytes(data: bytes) -> bytes:
    """Validate the PNG container and return its exact prefix through IEND.

    Checks chunk lengths/types/CRCs, IHDR dimensions/format, IDAT order and IEND.
    No pixel decode, recompression, color transform, or metadata rewriting occurs.
    Bytes after IEND are intentionally excluded, never interpreted as more chunks.
    Raises ValueError for malformed/truncated PNG data before or including IEND.
    """
    if not isinstance(data, bytes):
        raise TypeError("PNG data must be bytes")
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("PNG signature missing")
    offset = len(PNG_SIGNATURE)
    seen_header = False
    seen_data = False
    data_ended = False
    seen_palette = False
    color_type = None
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError("Truncated PNG chunk header/CRC")
        length = struct.unpack_from(">I", data, offset)[0]
        tag = data[offset + 4:offset + 8]
        if length > 0x7fffffff or length > len(data) - offset - 12:
            raise ValueError("PNG chunk length exceeds available data or format limit")
        if not all(65 <= byte <= 90 or 97 <= byte <= 122 for byte in tag) or tag[2] & 32:
            raise ValueError("Invalid PNG chunk type")
        body = data[offset + 8:offset + 8 + length]
        crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
        if zlib.crc32(tag + body) & 0xffffffff != crc:
            raise ValueError("PNG chunk CRC mismatch: " + tag.decode("ascii"))
        offset += length + 12
        if not seen_header and tag != b"IHDR":
            raise ValueError("IHDR must be the first PNG chunk")
        if tag == b"IHDR":
            if seen_header or length != 13:
                raise ValueError("Duplicate or invalid IHDR")
            width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
            if not (0 < width <= 0x7fffffff and 0 < height <= 0x7fffffff):
                raise ValueError("Invalid PNG dimensions")
            if depth not in depths.get(color_type, set()) or compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise ValueError("Invalid PNG IHDR format")
            seen_header = True
        elif tag == b"PLTE":
            if seen_palette or seen_data or length == 0 or length % 3 or length > 768 or color_type in (0, 4):
                raise ValueError("Invalid PNG palette")
            seen_palette = True
        elif tag == b"IDAT":
            if data_ended or (color_type == 3 and not seen_palette):
                raise ValueError("Invalid PNG image-data order/palette")
            seen_data = True
        elif tag == b"IEND":
            if length != 0 or not seen_data:
                raise ValueError("Invalid PNG IEND or missing IDAT")
            return data[:offset]
        else:
            if not tag[0] & 32:
                raise ValueError("Unknown critical PNG chunk: " + tag.decode("ascii"))
            if seen_data:
                data_ended = True
    raise ValueError("PNG IEND missing")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _immutable(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError("Preserve differing derived output: " + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def prepare_canonical_captures():
    from PIL import Image
    proof_data = PROOF.read_bytes()
    proof = json.loads(proof_data)
    if proof.get("passed") is not True or proof.get("restored") is not True:
        raise RuntimeError("Only a successful, restored Adaptive proof may supply captures")
    if not isinstance(proof.get("captures"), dict) or not proof["captures"]:
        raise RuntimeError("Successful proof has no pinned captures")
    pending = {}
    records = {}
    raw_hashes = {}
    filenames = set()
    for label, record in proof["captures"].items():
        filename = record["file"]
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".png"):
            raise RuntimeError("Proof capture must have a plain PNG filename")
        if filename in filenames:
            raise RuntimeError("Proof captures contain a duplicate filename")
        filenames.add(filename)
        raw = (GALLERY / filename).read_bytes()
        if _sha(raw) != record["sha256"]:
            raise RuntimeError("Raw capture hash differs from proof: " + filename)
        canonical = canonical_png_bytes(raw)
        # Decode only to verify losslessness. Output remains the exact original prefix.
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            size, mode = image.size, image.mode
            raw_pixels = _sha(image.convert("RGBA").tobytes())
        with Image.open(io.BytesIO(canonical)) as image:
            image.load()
            canonical_pixels = _sha(image.convert("RGBA").tobytes())
            if image.size != size or image.mode != mode or canonical_pixels != raw_pixels:
                raise RuntimeError("Canonical pixel comparison failed: " + filename)
        pending[DESTINATION / filename] = canonical
        raw_hashes[filename] = record["sha256"]
        records[label] = {"raw_file": filename, "raw_sha256": record["sha256"],
                          "display_file": "AdaptiveCanonical/" + filename, "display_sha256": _sha(canonical),
                          "raw_bytes": len(raw), "display_bytes": len(canonical),
                          "trailer_bytes": len(raw) - len(canonical), "dimensions": list(size), "mode": mode,
                          "decoded_rgba_sha256": raw_pixels, "decoded_pixels_identical": True}
    receipt = {"schema_version": 1, "passed": True,
               "generator_source": "Tools/UsfMaterials/canonical_capture_png.py",
               "generator_sha256": _sha(Path(__file__).read_bytes()),
               "proof_file": PROOF.name, "proof_sha256": _sha(proof_data),
               "capture_count": len(records), "captures": records,
               "pixel_preservation_method": "Exact original byte prefix through CRC-validated IEND; IDAT and all preceding chunks retained byte-identically. No reencode, resize, color conversion or metadata rewrite. Raw/canonical RGBA decode hashes also compared.",
               "source_cause": "UE5.8 Engine/Source/Runtime/Engine/Private/ImageUtils.cpp:1280 ExportRenderTarget2DAsPNG serializes CompressedData.GetAllocatedSize() instead of Num(), retaining allocation slack after valid PNG data. No raw trailer bytes are copied to this receipt.",
               "raw_captures_unchanged": True, "raw_proof_unchanged": True}
    receipt_data = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    pending[RECEIPT] = receipt_data
    # Complete validation and conflict checks before creating any derived file.
    for path, data in pending.items():
        if not path.resolve().is_relative_to(GALLERY.resolve()):
            raise RuntimeError("Derived destination escaped gallery")
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError("Preserve differing derived output: " + str(path))
    if PROOF.read_bytes() != proof_data:
        raise RuntimeError("Concurrent proof change; no derived outputs written")
    for filename, digest in raw_hashes.items():
        if _sha((GALLERY / filename).read_bytes()) != digest:
            raise RuntimeError("Concurrent raw capture change; no derived outputs written")
    for path, data in pending.items():
        _immutable(path, data)
    if PROOF.read_bytes() != proof_data or any(_sha((GALLERY / filename).read_bytes()) != digest for filename, digest in raw_hashes.items()):
        raise RuntimeError("Raw proof/capture changed during canonicalization; inspect before acceptance")
    summary = {"captures": len(records), "captures_with_trailers": sum(item["trailer_bytes"] > 0 for item in records.values()),
               "excluded_trailer_bytes": sum(item["trailer_bytes"] for item in records.values()),
               "pixel_comparisons_passed": len(records), "receipt": str(RECEIPT.relative_to(ROOT)),
               "receipt_sha256": _sha(receipt_data)}
    print(json.dumps(summary, indent=2))
    return receipt


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare_canonical_captures()


if __name__ == "__main__":
    main()
