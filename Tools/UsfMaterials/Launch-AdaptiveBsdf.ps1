param([switch]$Test, [switch]$Build, [switch]$Blendable, [switch]$BuildOnly, [switch]$ReuseDiscovery)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$editorLog = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
if (Test-Path -LiteralPath $editorLog) {
    try { [IO.File]::Open($editorLog, 'Open', 'Write', 'None').Close() }
    catch { throw 'Preserve and close the project editor before this renderer-profile launch.' }
}
$previous = [Environment]::GetEnvironmentVariable('UE-CmdLineArgs', 'Process')
if ($previous) { throw 'UE-CmdLineArgs is already set; inspect it before launching.' }
$profile = '-ini:Engine:[/Script/Engine.RendererSettings]:r.Substrate.ProjectGBufferFormat=1,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixel=4,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixelOverride=1,[/Script/Engine.RendererSettings]:r.AntiAliasingMethod=2'
$arguments = @("--project=$projectRoot")
if ($ReuseDiscovery -and -not $Test) { throw 'ReuseDiscovery applies only to tests using the same built binaries.' }
if ($BuildOnly) {
    if ($Test -or $Build -or $Blendable) { throw 'BuildOnly cannot combine with test/profile switches.' }
    $name = 'AdaptiveBsdf-ProfileIntegrationBuild'
    $arguments += @('--build', "--output=Saved/Logs/$name.log")
    $profile = ''
} elseif ($Test) {
    $name = if ($Blendable) { 'AdaptiveBsdf-BlendableGate' } else { 'AdaptiveBsdf-AdaptiveGate' }
    $pattern = if ($Blendable) { 'CkUsf' } else { 'AdaptiveBsdf' }
    $arguments += @('--test', "--test-pattern=$pattern", '--include-engine', '--no-nullrhi', '--parallel=1', '--no-live', '--known-reds=off', "--output=Saved/Logs/$name.log")
    if (-not $ReuseDiscovery) { $arguments += '--discover-fresh' }
    if ($Build) { $arguments += '--build' }
} else {
    if ($Blendable -or $Build) { throw 'Build/Blendable switches require -Test.' }
    $scriptPath = (Join-Path $PSScriptRoot 'adaptive_bsdf_session.py').Replace('\', '/')
    $arguments += '--launch-editor'
    $profile += ' -ExecCmds="py ' + $scriptPath + '"'
}
if ($Blendable) { $profile = '' }
try {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', ('-RenderOffscreen -unattended -nosplash -nosound ' + $profile), 'Process')
    $process = Start-Process -FilePath (Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe') -ArgumentList $arguments -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
    Write-Output "Offscreen renderer profile Toolbox PID $($process.Id)"
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
