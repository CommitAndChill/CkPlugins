"""Prove the refined aluminum still responds to .ush edits in the same master/MID."""
import hashlib
import json
from verify_industrial_reload import command, wait_reload, SHADERS, LOG, OUTPUT
from verify_batch1_reload import capture


def main():
    path = SHADERS / 'Looks/LibraryAluminum.ush'
    original = path.read_bytes()
    needle = b'return CkUsf_LibraryInspect(O, DebugView);'
    if original.count(needle) != 1:
        raise RuntimeError('Expected unique source anchor')
    edited = original.replace(needle, b'O.BaseColor *= 0.1; return CkUsf_LibraryInspect(O, DebugView);')
    report = {'passed': False, 'restored': False, 'stages': {}}
    try:
        command('select', '--look', 'LibraryAluminum', '--debug', 1)
        initial = command('library_proof_begin')
        report['pid'] = initial['pid']
        baseline = capture('Aluminum-v2-baseline', ['LibraryAluminum'], initial)
        report['stages']['baseline'] = baseline
        offset = LOG.stat().st_size
        path.write_bytes(edited)
        report['edit_reload'] = wait_reload(offset)
        changed = capture('Aluminum-v2-edited', ['LibraryAluminum'], initial)
        report['stages']['edited'] = changed
        if path.read_bytes() != edited:
            raise RuntimeError('Concurrent shader changes detected')
        offset = LOG.stat().st_size
        path.write_bytes(original)
        report['restore_reload'] = wait_reload(offset)
        recovered = capture('Aluminum-v2-restored', ['LibraryAluminum'], initial)
        report['stages']['recovered'] = recovered
        value = lambda data: data['LibraryAluminum']['mean_display_rgb']
        if value(changed) >= value(baseline) * 0.85 or abs(value(recovered) - value(baseline)) >= 0.02:
            raise RuntimeError('Rendered source edit/recovery did not match')
        report['passed'] = True
    finally:
        if path.read_bytes() == edited:
            offset = LOG.stat().st_size
            path.write_bytes(original)
            report['finally_reload'] = wait_reload(offset)
        report['restored'] = path.read_bytes() == original
        report['passed'] = report['passed'] and report['restored']
        report['source_sha256'] = hashlib.sha256(original).hexdigest()
        (OUTPUT / 'Aluminum-LiveReloadProof.json').write_text(json.dumps(report, indent=2))
        command('proof_end')
        command('select', '--look', 'LibraryAluminum', '--debug', 0)
    print(json.dumps({'passed': report['passed'], 'restored': report['restored'], 'pid': report.get('pid')}))


if __name__ == '__main__':
    main()
