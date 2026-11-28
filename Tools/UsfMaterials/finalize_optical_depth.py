"""Record clean closure of the already-quit owned studio; never terminate processes."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/UsfMaterialGallery'

def main(toolbox_pid):
    assert toolbox_pid>0
    quit_record=json.loads((OUT/'OpticalDepth-Quit.json').read_text())
    assert quit_record['ok'] and quit_record['result']['quit_requested']
    editor_pid=quit_record['pid'];assert isinstance(editor_pid,int) and editor_pid>0
    script=f"$active = @(Get-Process -Id {editor_pid},{toolbox_pid} -ErrorAction SilentlyContinue); if ($active.Count) {{ exit 90 }}; exit 0"
    for attempt in range(20):
        code=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True).returncode
        if code==0:break
        assert code==90,'Process check failed'
        time.sleep(.5)
    else:raise RuntimeError('Owned editor/Toolbox still active; preserve it and inspect')
    source=ROOT/'Saved/Logs/CkPlugins.log';data=source.read_bytes();log=data.decode(errors='replace')
    markers=['Error:','Ensure condition failed','Fatal error','AS_COMPILE_FAILED','Traceback']
    matches=[line for line in log.splitlines() if any(marker in line for marker in markers)]
    assert not matches,matches
    assert 'LogExit: Exiting.' in log and 'Log file closed' in log
    target=OUT/'OpticalDepth-Final.log';shutil.copyfile(source,target)
    record=dict(editor_pid=editor_pid,toolbox_pid=toolbox_pid,session_id=quit_record['session_id'],
                editor_and_toolbox_absent_from_process_check=True,clean_shutdown_marker=True,
                error_ensure_traceback_matches=matches,log=target.name,log_sha256=hashlib.sha256(data).hexdigest())
    (OUT/'OpticalDepth-FinalSession.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolbox-pid',type=int,required=True,help='Owned Toolbox PID printed by this launch')
    main(parser.parse_args().toolbox_pid)
