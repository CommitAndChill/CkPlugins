$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$toolbox = Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe'
$scriptPath = (Join-Path $PSScriptRoot 'start_studio_session.py').Replace('\', '/')
$previous = [Environment]::GetEnvironmentVariable('UE-CmdLineArgs', 'Process')
if ($previous) { throw 'UE-CmdLineArgs is already set; preserve and inspect it before launching.' }
try {
    # LaunchEngineLoop explicitly appends this process-local variable. The editor renders without a desktop window.
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', ('-RenderOffscreen -unattended -nosplash -nosound -ExecCmds="py ' + $scriptPath + '"'), 'Process')
    $process = Start-Process -FilePath $toolbox -ArgumentList @('--launch-editor', "--project=$projectRoot") -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
    Write-Output "Offscreen studio Toolbox PID $($process.Id); watch Saved/Logs/CkPlugins.log and StudioResult.json"
} finally {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', $previous, 'Process')
}
