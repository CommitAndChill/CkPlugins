"""Native three-level diffuse ramp refinement, outside PIE. Retains the factory profile."""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
FOLDER = '/CkFoundation/CkUsf/Profiles'
OWNER = 'CkUsf.NativeToonRamp.v1'
KEYS = [(0, .10), (.54, .10), (.55, .45), (.79, .45), (.80, 1), (1, 1)]


def prepare():
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('End PIE before profile authoring')
    profile = unreal.load_asset(FOLDER + '/TP_CkUsf_NativeCeramic')
    if not isinstance(profile, unreal.ToonProfile) or unreal.EditorAssetLibrary.get_metadata_tag(profile, 'CkUsf.NativeBsdfPreparation.v1') != '1':
        raise RuntimeError('Expected the owned native ceramic profile')
    baseline_path = FOLDER + '/TP_CkUsf_NativeCeramic_FactoryBaseline'
    curve_path = FOLDER + '/Curve_NativeCeramic_ThreeLevels'
    if any(unreal.EditorAssetLibrary.does_asset_exist(p) for p in [baseline_path, curve_path]):
        raise RuntimeError('Preserve existing ramp assets; this refinement is initial-only')
    settings = profile.get_editor_property('settings')
    ramp = settings.get_editor_property('diffuse_ramp')
    if ramp.get_editor_property('external_curve'):
        raise RuntimeError('Preserve the existing custom diffuse curve')
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    baseline = tools.duplicate_asset('TP_CkUsf_NativeCeramic_FactoryBaseline', FOLDER, profile)
    if not baseline:
        raise RuntimeError('Cannot preserve factory profile')
    unreal.EditorAssetLibrary.set_metadata_tag(baseline, OWNER, 'factory-baseline')
    if not unreal.EditorAssetLibrary.save_loaded_asset(baseline, only_if_is_dirty=False):
        raise RuntimeError('Cannot save factory baseline')
    csv = ROOT / 'Tools/UsfMaterials/NativeCeramicThreeLevels.csv'
    factory = unreal.CSVImportFactory()
    options = unreal.CSVImportSettings()
    options.set_editor_property('import_type', type(options.get_editor_property('import_type')).cast(4))
    factory.set_editor_property('automated_import_settings', options)
    task = unreal.AssetImportTask()
    for key, value in {'filename': str(csv), 'destination_path': FOLDER,
                       'destination_name': 'Curve_NativeCeramic_ThreeLevels',
                       'automated': True, 'save': True, 'replace_existing': False, 'factory': factory}.items():
        task.set_editor_property(key, value)
    tools.import_asset_tasks([task])
    curve = unreal.load_asset(curve_path)
    if not isinstance(curve, unreal.CurveLinearColor):
        raise RuntimeError('Native diffuse curve import failed')
    for time, value in KEYS:
        sample = curve.get_linear_color_value(time)
        if any(abs(getattr(sample, channel)-value) > 1e-4 for channel in ['r', 'g', 'b']):
            raise RuntimeError('Imported ramp differs from the explicit three-level recipe')
    unreal.EditorAssetLibrary.set_metadata_tag(curve, OWNER, 'three-level-diffuse')
    if not unreal.EditorAssetLibrary.save_loaded_asset(curve, only_if_is_dirty=False):
        raise RuntimeError('Cannot save native diffuse curve metadata')
    ramp.set_editor_property('external_curve', curve)
    settings.set_editor_property('diffuse_ramp', ramp)
    profile.set_editor_property('settings', settings)
    if not unreal.EditorAssetLibrary.save_loaded_asset(profile, only_if_is_dirty=False):
        raise RuntimeError('Cannot save the refined native Toon profile')
    report = {'profile': profile.get_path_name(), 'factory_baseline': baseline.get_path_name(),
              'curve': curve.get_path_name(), 'keys': KEYS, 'changed': 'Diffuse ramp only; specular, GI, patterns, textures and lights retained'}
    (ROOT/'Saved/UsfMaterialGallery/NativeToonProfile.json').write_text(json.dumps(report, indent=2))
    return report
