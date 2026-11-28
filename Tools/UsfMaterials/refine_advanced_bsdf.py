"""Persist the reviewed carbon/copper numeric defaults; explicit regeneration outside PIE."""
import hashlib
import importlib
import json
from pathlib import Path
import unreal
import advanced_bsdf_settings


def prepare():
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('End PIE before changing native master defaults')
    recipes = importlib.reload(advanced_bsdf_settings).LOOKS
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    candidates = []
    for name in ['NativeResinCarbon', 'NativeCopper']:
        definition = unreal.load_asset('/CkFoundation/CkUsf/Looks/Native/DA_'+name)
        master = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_'+name)
        if not definition or not isinstance(master, unreal.Material):
            raise RuntimeError('Prepare the native example before refinement: '+name)
        if (unreal.EditorAssetLibrary.get_metadata_tag(definition, 'CkUsf.AdvancedBsdfPreparation.v1') != '1' or
            unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != definition.get_path_name()):
            raise RuntimeError('Refinement destination ownership differs: '+name)
        scalars = dict(recipes[name]['scalars'])
        vectors = dict(recipes[name]['vectors'])
        params = definition.get_editor_property('_Parameters')
        before = {}
        seen = set()
        for param in params:
            key = str(param.get_editor_property('_Name'))
            if key in scalars:
                before[key] = param.get_editor_property('_DefaultScalar')
                param.set_editor_property('_DefaultScalar', scalars[key])
                seen.add(key)
            elif key in vectors:
                previous = param.get_editor_property('_DefaultVector')
                before[key] = [getattr(previous, axis) for axis in ['r', 'g', 'b', 'a']]
                param.set_editor_property('_DefaultVector', unreal.LinearColor(*vectors[key]))
                seen.add(key)
        if seen != set(scalars) | set(vectors):
            raise RuntimeError('Existing parameter layout differs: '+name)
        candidates.append((name, definition, params, before))
    generator = unreal.get_editor_subsystem(unreal.load_class(None, '/Script/CkUsfEditor.CkUsf_GeneratorSubsystem'))
    report = {'settings_sha256': hashlib.sha256((root/'Tools/UsfMaterials/advanced_bsdf_settings.py').read_bytes()).hexdigest(), 'looks': {}}
    for name, definition, params, before in candidates:
        definition.set_editor_property('_Parameters', params)
        if not unreal.EditorAssetLibrary.save_loaded_asset(definition, only_if_is_dirty=False):
            raise RuntimeError('Cannot save refined definition: '+name)
        generator.generate_look_material_for(definition)
        master = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_'+name)
        errors = unreal.MaterialEditingLibrary.recompile_material(master)
        if errors:
            raise RuntimeError('Refined native compilation failed: '+str(errors))
        if not unreal.EditorAssetLibrary.save_loaded_asset(master, only_if_is_dirty=False):
            raise RuntimeError('Cannot save refined native master: '+name)
        report['looks'][name] = {'before': before, 'scalars': dict(recipes[name]['scalars']),
                                 'vectors': dict(recipes[name]['vectors']), 'master': master.get_path_name()}
    (root/'Saved/UsfMaterialGallery/AdvancedBsdfRefinement.json').write_text(json.dumps(report, indent=2))
    return report
