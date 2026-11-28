"""Ordered source-backed native BSDF recipes; imported by preparation/capture tooling.

Numeric defaults are authored presentation choices, not measured optical calibration.
No asset mutation or Unreal import occurs in this module. Parameter order is textures,
then vectors, then scalars; each list order matches its .ush entrypoint exactly.
Poly Haven source BC16 must use the verified encoded-RGB-to-BC8 runtime recipe;
velvet source NPOT 1024x985 is retained and runtime resizing must be recorded.
"""

TEXTURE_PARAMETERS = [
    ("BaseColorMap", "BaseColor"),
    ("NormalMap", "Normal"),
    ("RoughnessMap", "Roughness"),
]

LOOKS = {
    "NativeRubyVelvet": {
        "source_batch": "Batch3Textures",
        "source_key": "velvet",
        "runtime_basename": "LibraryVelvet",
        "surface_graph": 1,
        "slab_fuzz": True,
        "directional_shading": False,
        "identity_notes": "CC0 Poly Haven velour_velvet: real napped velour, not geometric pile. Fuzz is engine-owned.",
        "vectors": [
            ("TintColor", (1.0, 0.8, 0.9, 1.0)),
            ("FuzzTint", (0.45, 0.12, 0.18, 1.0)),
        ],
        "scalars": [
            ("UVScale", 2.0),
            ("UVRotation", 0.0),
            ("NormalStrength", 0.18),
            ("RoughnessScale", 0.85),
            ("RoughnessBias", 0.05),
            ("DebugView", 0.0),
            ("FuzzWeight", 0.9),
        ],
    },
    "NativeVarnishedWalnut": {
        "source_batch": "Batch3Textures",
        "source_key": "walnut",
        "runtime_basename": "LibraryWalnut",
        "surface_graph": 3,
        "slab_fuzz": False,
        "directional_shading": False,
        "identity_notes": "CC0 Poly Haven walnut_veneer_02: clean veneer. Varnish is independently authored native coating.",
        "vectors": [
            ("TintColor", (0.72, 0.43, 0.22, 1.0)),
        ],
        "scalars": [
            ("UVScale", 0.9),
            ("UVRotation", 0.0),
            ("NormalStrength", 0.18),
            ("RoughnessScale", 0.7),
            ("RoughnessBias", 0.03),
            ("DebugView", 0.0),
            ("CoatWeight", 0.85),
            ("CoatRoughness", 0.18),
            ("GrainContrast", 1.1),
        ],
    },
    "NativeResinCarbon": {
        "source_batch": "Batch3Textures",
        "source_key": "carbon_fiber",
        "runtime_basename": "LibraryCarbonFiber",
        "surface_graph": 3,
        "slab_fuzz": False,
        "directional_shading": False,
        "identity_notes": "CC0 ambientCG Fabric004: crossed-tow carbon-tagged weave. Resin is authored; carbon remains dielectric.",
        "vectors": [
            ("TintColor", (1.0, 1.0, 1.0, 1.0)),
        ],
        "scalars": [
            ("UVScale", 12.0),
            ("UVRotation", 45.0),
            ("NormalStrength", 0.04),
            ("RoughnessScale", 0.7),
            ("RoughnessBias", 0.18),
            ("DebugView", 0.0),
            ("CoatWeight", 0.95),
            ("CoatRoughness", 0.13),
            ("TowContrast", 1.05),
        ],
    },
    "NativeCopper": {
        "source_batch": "Batch7Textures",
        "source_key": "copper",
        "runtime_basename": "LibraryCopper",
        "surface_graph": 1,
        "slab_fuzz": False,
        "directional_shading": False,
        "identity_notes": "CC0 ambientCG Metal057A: clean copper finish, no patina. Isotropic conductor; no fabricated brush direction.",
        "vectors": [
            ("TintColor", (0.95, 0.48, 0.28, 1.0)),
        ],
        "scalars": [
            ("UVScale", 2.0),
            ("UVRotation", 0.0),
            ("NormalStrength", 0.1),
            ("RoughnessScale", 2.5),
            ("RoughnessBias", 0.13),
            ("DebugView", 0.0),
            ("MetalColorVariation", 0.2),
        ],
    },
}
