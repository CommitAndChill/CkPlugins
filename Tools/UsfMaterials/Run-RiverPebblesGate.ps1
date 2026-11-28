$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$log = 'Saved/Logs/UsfLibrary-RiverPebbles.log'
$arguments = @("--project=$projectRoot", "--output=$log", '--test',
    '--test-pattern=GeneratesUsableMasters', '--no-live', '--no-nullrhi', '--parallel=1',
    '--known-reds=off', '--editor-args="-CkUsfSubstrateProof -RenderOffscreen"')
$process = Start-Process -FilePath (Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe') -ArgumentList $arguments -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
Write-Output "River pebbles and orbit focused Toolbox PID $($process.Id), log $log"
$process.WaitForExit()
$process.Refresh()
$receipt = @{ pid = $process.Id; exit_code = $process.ExitCode; log = $log; completed_utc = [DateTime]::UtcNow.ToString('o') }
$receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot 'Saved/UsfMaterialGallery/RiverPebbles-Gate.exit.json')
Write-Output ($receipt | ConvertTo-Json -Compress)
exit $process.ExitCode
