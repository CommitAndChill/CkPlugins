$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$editorLog = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
if (Test-Path -LiteralPath $editorLog) {
    try { [IO.File]::Open($editorLog, 'Open', 'Write', 'None').Close() }
    catch { throw 'Preserve and close the project editor before this separate optical-profile launch.' }
}
$previous = [Environment]::GetEnvironmentVariable('UE-CmdLineArgs', 'Process')
if ($previous) { throw 'UE-CmdLineArgs is already set; inspect before launching.' }
$profile = '-ini:Engine:[/Script/Engine.RendererSettings]:r.Substrate.ProjectGBufferFormat=1,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixel=4,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixelOverride=1,[/Script/Engine.RendererSettings]:r.AntiAliasingMethod=2'
$scriptPath = (Join-Path $PSScriptRoot 'amber_specimen_session.py').Replace('\', '/')
try {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', ('-RenderOffscreen -unattended -nosplash -nosound ' + $profile + ' -ExecCmds="py ' + $scriptPath + '"'), 'Process')
    $process = Start-Process -FilePath (Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe') -ArgumentList @("--project=$projectRoot", '--launch-editor') -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
    Write-Output "Offscreen amber Toolbox PID $($process.Id)"
} finally {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', $previous, 'Process')
}
