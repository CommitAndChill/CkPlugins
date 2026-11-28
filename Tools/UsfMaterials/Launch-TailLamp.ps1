param([switch]$BuildOnly, [switch]$Test, [switch]$Build, [switch]$Blendable, [switch]$ReuseDiscovery)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$editorLog = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
if (Test-Path -LiteralPath $editorLog) {
    try { [IO.File]::Open($editorLog, 'Open', 'Write', 'None').Close() }
    catch { throw 'Preserve and close the project editor before this optical-profile launch.' }
}
$previous = [Environment]::GetEnvironmentVariable('UE-CmdLineArgs', 'Process')
if ($previous) { throw 'UE-CmdLineArgs is already set; inspect it before launching.' }
$profile = '-ini:Engine:[/Script/Engine.RendererSettings]:r.Substrate.ProjectGBufferFormat=1,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixel=4,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixelOverride=1,[/Script/Engine.RendererSettings]:r.AntiAliasingMethod=2'
$arguments = @("--project=$projectRoot")
if ($BuildOnly) {
    if ($Test -or $Build -or $Blendable) { throw 'BuildOnly cannot combine with other switches.' }
    $name = 'TailLamp-IntegrationBuild'
    $arguments += @('--build', "--output=Saved/Logs/$name.log")
    $profile = ''
} elseif ($Test) {
    $name = if ($Blendable) { 'TailLamp-BlendableGate' } else { 'TailLamp-AdaptiveGate' }
    $pattern = if ($Blendable) { 'CkUsf' } else { 'OpticalTailLamp' }
    $arguments += @('--test', "--test-pattern=$pattern", '--include-engine', '--no-nullrhi', '--parallel=1', '--no-live', '--known-reds=off', "--output=Saved/Logs/$name.log")
    if (-not $ReuseDiscovery) { $arguments += '--discover-fresh' }
    if ($Build) { $arguments += '--build' }
} else {
    if ($Build -or $Blendable -or $ReuseDiscovery) { throw 'Gate switches require -Test.' }
    $arguments += '--launch-editor'
    $scriptPath = (Join-Path $PSScriptRoot 'tail_lamp_session.py').Replace('\', '/')
    $profile += ' -ExecCmds="py ' + $scriptPath + '"'
    $name = 'TailLamp-Studio'
}
if ($Blendable) { $profile = '' }
try {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', ('-RenderOffscreen -unattended -nosplash -nosound ' + $profile), 'Process')
    $process = Start-Process -FilePath (Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe') -ArgumentList $arguments -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
    Write-Output "Offscreen optical Toolbox PID $($process.Id)"
    if ($Test -or $BuildOnly) {
        $process.WaitForExit()
        $process.Refresh()
        $receipt = @{ pid=$process.Id; exit_code=$process.ExitCode; profile=$name; completed_utc=[DateTime]::UtcNow.ToString('o') }
        $receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot "Saved/UsfMaterialGallery/$name-process.json")
        Write-Output ($receipt | ConvertTo-Json -Compress)
        exit $process.ExitCode
    }
} finally {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', $previous, 'Process')
}
