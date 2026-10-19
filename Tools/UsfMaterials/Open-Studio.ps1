$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$toolbox = Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe'
if (-not (Test-Path -LiteralPath $toolbox)) { throw 'UnrealToolbox is missing from this checkout' }
$projectEditors = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^CkPluginsEditor(-Cmd)?\.exe$' -and $_.CommandLine -like "*$projectRoot*"
})
if ($projectEditors.Count -eq 0) {
    Start-Process -FilePath $toolbox -ArgumentList @('--launch-editor', "--project=$projectRoot") -WindowStyle Hidden | Out-Null
}
Write-Host 'Once the editor is ready, run this in its console (outside PIE):'
$pythonFile = (Join-Path $PSScriptRoot 'open_studio_in_editor.py').Replace('\', '/')
Write-Host ('py "' + $pythonFile + '"')
