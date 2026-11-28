"""Ordered numeric/binding recipes for the first two Adaptive native graphs.

Parameter order is textures (each followed by its sampler), then vectors, then scalars.
Receipt.json pins CC0 backing and authored yarn utilities. These are independent art
interpretations, not supplied Zorah/Fab assets or calibrated material measurements.
Two Slabs per look: Vertical dye-over-metal; Horizontal independently oriented silk.
"""

SOURCE_RECEIPT = "Plugins/CkTests/Resources/CkUsf/AdaptiveBsdfV1/Receipt-v2.json"
LOOKS = {
    "AdaptiveCandyPaint": {
        "surface_graph": 4,
        "directional_shading": False,
        "identity_notes": "Two native Slabs: authored red dyed transmitting medium over neutral conductor. Plastic010/copper microfinish reused; no third clearcoat, scanned candy paint or metallic-flake claim.",
        "textures": [
            ("BaseColorMap", "paint_metal", "BaseColor"),
            ("NormalMap", "paint_surface", "Normal"),
            ("RoughnessMap", "paint_surface", "Roughness"),
            ("MetalNormalMap", "paint_metal", "Normal"),
            ("MetalRoughnessMap", "paint_metal", "Roughness"),
        ],
        "vectors": [
            ("TintColor", (1.0, 1.0, 1.0, 1.0)),
            ("DyeTransmittance", (0.92, 0.15, 0.025, 1.0)),
            ("MetalTint", (0.9, 0.9, 0.9, 1.0)),
        ],
        "scalars": [
            ("UVScale", 4.0),
            ("UVRotation", 0.0),
            ("NormalStrength", 0.12),
            ("RoughnessScale", 1.0),
            ("RoughnessBias", 0.0),
            ("DebugView", 0.0),
            ("MetalNormalStrength", 0.1),
            ("MetalRoughnessScale", 2.6),
            ("MetalRoughnessBias", 0.12),
            ("TopRoughnessScale", 0.16),
            ("TopRoughnessBias", 0.045),
            ("ThicknessCm", 0.006),
            ("DyeReferenceThicknessCm", 0.006),
            ("ThicknessVariation", 0.3),
            ("MetalColorVariation", 0.12),
        ],
    },
    "AdaptiveSlubSilk": {
        "surface_graph": 5,
        "directional_shading": True,
        "identity_notes": "CC0 Poly Haven crepe_satin backing plus original neutral radius-profile slub maps. Two independent native anisotropic Slabs; authored slubbed interpretation, not a slub scan or Zorah asset copy.",
        "textures": [
            ("BaseColorMap", "silk", "BaseColor"),
            ("NormalMap", "silk", "Normal"),
            ("RoughnessMap", "silk", "Roughness"),
            ("DirectionMap", "silk", "Direction"),
            ("AnisotropyMap", "silk", "Anisotropy"),
            ("SlubMask", "utility", "SlubMask"),
            ("SlubNormalMap", "utility", "SlubNormal"),
        ],
        "vectors": [
            ("TintColor", (0.75, 0.9, 1.0, 1.0)),
            ("SecondaryTint", (0.85, 0.92, 1.0, 1.0)),
        ],
        "scalars": [
            # Actual shader-ball UV Jacobians put physical source scale near 11.5.
            # Four deliberately magnifies yarn detail for this inspection study.
            ("UVScale", 4.0),
            ("UVRotation", 0.0),
            ("NormalStrength", 0.5),
            ("RoughnessScale", 1.0),
            ("RoughnessBias", 0.0),
            ("DebugView", 0.0),
            ("SlubStrength", 1.5),
            ("SlubColorVariation", 0.08),
            ("DirectionInfluence", 0.25),
            ("LobeARotation", 0.0),
            ("LobeBRotation", 90.0),
            ("AnisotropyA", 0.9),
            ("AnisotropyB", 0.7),
            ("LobeARoughnessScale", 0.3),
            ("LobeARoughnessBias", 0.06),
            ("LobeBRoughnessScale", 0.9),
            ("LobeBRoughnessBias", 0.16),
            ("LobeWeight", 0.6),
            ("SlubWeightVariation", 0.15),
        ],
    },
}
