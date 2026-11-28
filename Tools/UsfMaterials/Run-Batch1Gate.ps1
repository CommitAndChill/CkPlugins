param([ValidateSet('Build', 'Test', 'ToonRetry', 'Aluminum')][string]$Mode = 'Test')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$toolbox = Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe'
$log = "Saved/Logs/UsfLibrary-$Mode.log"
$arguments = @("--project=$projectRoot", "--output=$log")
if ($Mode -eq 'Build') {
    $logPath = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
    if (Test-Path -LiteralPath $logPath) {
        try { [IO.File]::Open($logPath, 'Open', 'Write', 'None').Close() }
        catch { throw 'The project editor still holds its log. Close it before building.' }
    }
    $arguments += '--build'
} else {
    $pattern = switch ($Mode) {
        'ToonRetry' { 'ShadingModelDeclarationToonPipelineReloadUpdatesExistingMID' }
        'Aluminum' { 'GeneratesUsableMasters' }
        default { 'CkUsf' }
    }
    $arguments += @('--test', "--test-pattern=$pattern", '--no-live', '--no-nullrhi',
                    '--parallel=1', '--known-reds=off', '--editor-args=-CkUsfSubstrateProof')
    if ($Mode -eq 'Aluminum') {
        $arguments = $arguments | ForEach-Object {
            if ($_ -eq '--editor-args=-CkUsfSubstrateProof') { '--editor-args="-CkUsfSubstrateProof -RenderOffscreen"' } else { $_ }
        }
    }
}
$process = Start-Process -FilePath $toolbox -ArgumentList $arguments -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
Write-Output "Toolbox $Mode PID $($process.Id), log $log"
$process.WaitForExit()
$process.Refresh()
$receipt = @{ mode = $Mode; pid = $process.Id; exit_code = $process.ExitCode; log = $log; completed_utc = [DateTime]::UtcNow.ToString('o') }
$receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot "Saved/UsfMaterialGallery/Batch1-$Mode.exit.json")
Write-Output ($receipt | ConvertTo-Json -Compress)
exit $process.ExitCode
