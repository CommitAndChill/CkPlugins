$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$toolbox = Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe'
$log = 'Saved/Logs/UsfLibrary-Batch3Build.log'
$arguments = @("--project=$projectRoot", "--output=$log")
$logPath = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
if (Test-Path -LiteralPath $logPath) {
    try { [IO.File]::Open($logPath, 'Open', 'Write', 'None').Close() }
    catch { throw 'The project editor still holds its log. Close it before building.' }
}
$arguments += '--build'
$process = Start-Process -FilePath $toolbox -ArgumentList $arguments -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
Write-Output "Batch3 incremental build PID $($process.Id), log $log"
$process.WaitForExit()
$process.Refresh()
$receipt = @{ pid = $process.Id; exit_code = $process.ExitCode; log = $log; completed_utc = [DateTime]::UtcNow.ToString('o') }
$receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot 'Saved/UsfMaterialGallery/Batch3-Build.exit.json')
Write-Output ($receipt | ConvertTo-Json -Compress)
exit $process.ExitCode
