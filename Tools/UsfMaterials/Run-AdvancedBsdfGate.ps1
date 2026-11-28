$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$logPath = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
if (Test-Path -LiteralPath $logPath) {
    try { [IO.File]::Open($logPath, 'Open', 'Write', 'None').Close() }
    catch { throw 'The project editor holds its log. Preserve it before building.' }
}
$log = 'Saved/Logs/AdvancedBsdf-BuildTest1.log'
$arguments = @("--project=$projectRoot", "--output=$log", '--build', '--test',
    '--test-pattern=CkUsf', '--include-engine', '--no-nullrhi', '--parallel=1',
    '--no-live', '--discover-fresh', '--known-reds=off', '--editor-args=-RenderOffscreen')
$process = Start-Process -FilePath (Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe') -ArgumentList $arguments -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
Write-Output "Advanced BSDF incremental build and focused gate PID $($process.Id); $log"
$process.WaitForExit()
$process.Refresh()
$receipt = @{ pid = $process.Id; exit_code = $process.ExitCode; log = $log; completed_utc = [DateTime]::UtcNow.ToString('o') }
$receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot 'Saved/UsfMaterialGallery/AdvancedBsdf-Gate1-process.json')
Write-Output ($receipt | ConvertTo-Json -Compress)
exit $process.ExitCode
