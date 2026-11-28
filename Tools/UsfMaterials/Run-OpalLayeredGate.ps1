param([switch]$Build, [switch]$Blendable, [switch]$ReuseDiscovery, [string]$Suffix='')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if ($Suffix -notmatch '^[A-Za-z0-9-]*$') { throw 'Plain gate suffix required.' }
$editorLog = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
if (Test-Path -LiteralPath $editorLog) {
    try { [IO.File]::Open($editorLog, 'Open', 'Write', 'None').Close() }
    catch { throw 'Preserve and close the project editor before building/testing.' }
}
$previous = [Environment]::GetEnvironmentVariable('UE-CmdLineArgs', 'Process')
if ($previous) { throw 'UE-CmdLineArgs is already set; inspect before launching.' }
$name = 'OpalLayered-' + $(if ($Blendable) { 'BlendableGate' } else { 'AdaptiveGate' }) + $Suffix
$logPath = Join-Path $projectRoot "Saved/Logs/$name.log"
$receiptPath = Join-Path $projectRoot "Saved/UsfMaterialGallery/$name-process.json"
if ((Test-Path -LiteralPath $logPath) -or (Test-Path -LiteralPath $receiptPath)) { throw 'Preserve previous gate evidence; use a unique suffix.' }
$profile = '-ini:Engine:[/Script/Engine.RendererSettings]:r.Substrate.ProjectGBufferFormat=1,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixel=4,[/Script/Engine.RendererSettings]:r.Substrate.ProjectClosuresPerPixelOverride=1,[/Script/Engine.RendererSettings]:r.AntiAliasingMethod=2'
$pattern = if ($Blendable) { 'CkUsf' } else { 'AdaptiveBsdf' }
$arguments = @("--project=$projectRoot", '--test', "--test-pattern=$pattern", '--include-engine', '--no-nullrhi', '--parallel=1', '--no-live', '--known-reds=off', "--output=Saved/Logs/$name.log")
if (-not $ReuseDiscovery) { $arguments += '--discover-fresh' }
if ($Build) { $arguments += '--build' }
if ($Blendable) { $profile = '' }
try {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', ('-RenderOffscreen -unattended -nosplash -nosound ' + $profile), 'Process')
    $process = Start-Process -FilePath (Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe') -ArgumentList $arguments -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
    Write-Output "Offscreen layered-opal gate Toolbox PID $($process.Id)"
    $process.WaitForExit()
    $process.Refresh()
    $receipt = @{ pid=$process.Id; exit_code=$process.ExitCode; profile=$name; completed_utc=[DateTime]::UtcNow.ToString('o') }
    $receipt | ConvertTo-Json | Set-Content -LiteralPath $receiptPath
    Write-Output ($receipt | ConvertTo-Json -Compress)
    exit $process.ExitCode
} finally {
    [Environment]::SetEnvironmentVariable('UE-CmdLineArgs', $previous, 'Process')
}
