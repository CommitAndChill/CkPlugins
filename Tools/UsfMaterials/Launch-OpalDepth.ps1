$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$editorLog = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
if (Test-Path -LiteralPath $editorLog) {
    try { [IO.File]::Open($editorLog, 'Open', 'Write', 'None').Close() }
    catch { throw 'Preserve and close the project editor before this separate optical-profile launch.' }
}
$directory = Join-Path $projectRoot 'Saved/UsfMaterialGallery'
foreach ($filename in @('OpalDepthRequest.json', 'OpalDepthCommand.lock')) {
    if (Test-Path -LiteralPath (Join-Path $directory $filename)) {
        throw "Unresolved opal-depth command: $filename. Inspect ownership before relaunching."
    }
}
$previous = [Environment]::GetEnvironmentVariable('UE-CmdLineArgs', 'Process')
$previousIdentity = [Environment]::GetEnvironmentVariable('CK_OPAL_DEPTH_SESSION_ID', 'Process')
if ($previous -or $previousIdentity) { throw 'Optical launch environment already set; inspect before launching.' }
$identity = [guid]::NewGuid().ToString()
$profile = '-ini:Engine:[/Script/Engine.RendererSettings]:r.Substrate.ProjectGBufferFormat=1,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixel=4,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixelOverride=1,[/Script/Engine.RendererSettings]:r.AntiAliasingMethod=2'
$scriptPath = (Join-Path $PSScriptRoot 'opal_depth_session.py').Replace('\', '/')
try {
    [Environment]::SetEnvironmentVariable('CK_OPAL_DEPTH_SESSION_ID', $identity, 'Process')
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', ('-RenderOffscreen -unattended -nosplash -nosound ' + $profile + ' -ExecCmds="py ' + $scriptPath + '"'), 'Process')
    $process = Start-Process -FilePath (Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe') -ArgumentList @("--project=$projectRoot", '--launch-editor') -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
    Write-Output "Offscreen OpalDepth Toolbox PID $($process.Id); session $identity"
} finally {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', $previous, 'Process')
    [Environment]::SetEnvironmentVariable('CK_OPAL_DEPTH_SESSION_ID', $previousIdentity, 'Process')
}
