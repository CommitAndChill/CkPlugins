$ErrorActionPreference = 'Stop'
function Get-BytesHash([byte[]] $bytes) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($bytes)).Replace('-', '') }
    finally { $algorithm.Dispose() }
}
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$manifestPath = Join-Path $projectRoot 'Binaries/Win64/CkPluginsEditor.modules'
$targetPath = Join-Path $projectRoot 'Binaries/Win64/CkPluginsEditor.target'
$evidence = Join-Path $projectRoot 'Saved/UsfMaterialGallery/ObsoleteTextureManifest'
$logPath = Join-Path $projectRoot 'Saved/Logs/CkPlugins.log'
try { [IO.File]::Open($logPath, 'Open', 'Write', 'None').Close() }
catch { throw 'Preserve the running editor before reconciling its module manifest.' }
$before = [IO.File]::ReadAllBytes($manifestPath)
$beforeHash = Get-BytesHash $before
$manifest = [Text.Encoding]::UTF8.GetString($before) | ConvertFrom-Json
$targetBytes = [IO.File]::ReadAllBytes($targetPath)
$targetHash = Get-BytesHash $targetBytes
$target = [Text.Encoding]::UTF8.GetString($targetBytes) | ConvertFrom-Json
if ($target.Version.MajorVersion -ne 5 -or $target.Version.MinorVersion -ne 8 -or
    $manifest.BuildId -ne $target.Version.BuildId) { throw 'Receipt/manifest engine identity mismatch.' }
$names = @('TextureFormatDXT', 'TextureFormatIntelISPCTexComp')
$products = @($target.BuildProducts | ForEach-Object { $_.Path -replace '^.*[/\\]', '' })
$removed = @()
foreach ($name in $names) {
    $property = $manifest.Modules.PSObject.Properties[$name]
    if (-not $property -or $property.Value -ne "CkPluginsEditor-$name.dll") { throw "Unexpected entry: $name" }
    if ($products -contains $property.Value) { throw "Current target owns $name; do not remove it." }
    $file = Join-Path $projectRoot ('Binaries/Win64/' + $property.Value)
    $removed += @{ module = $name; binary = $property.Value; binary_sha256 = (Get-FileHash -LiteralPath $file).Hash }
}
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$backup = Join-Path $evidence 'CkPluginsEditor.modules.before.json'
if (Test-Path -LiteralPath $backup) { throw 'Preserve the existing repair evidence before another attempt.' }
[IO.File]::WriteAllBytes($backup, $before)
[IO.File]::WriteAllBytes((Join-Path $evidence 'CkPluginsEditor.target.before.json'), $targetBytes)
foreach ($name in $names) { $manifest.Modules.PSObject.Properties.Remove($name) }
$after = ($manifest | ConvertTo-Json -Depth 5) + "`r`n"
if ((Get-FileHash -LiteralPath $manifestPath).Hash -ne $beforeHash) { throw 'Concurrent manifest edit; backup retained.' }
if ((Get-FileHash -LiteralPath $targetPath).Hash -ne $targetHash) { throw 'Concurrent target receipt edit; backups retained.' }
[IO.File]::WriteAllText($manifestPath, $after, [Text.UTF8Encoding]::new($false))
foreach ($entry in $removed) {
    $file = Join-Path $projectRoot ('Binaries/Win64/' + $entry.binary)
    if ((Get-FileHash -LiteralPath $file).Hash -ne $entry.binary_sha256) { throw 'A preserved binary changed concurrently.' }
}
@{ build_id = $manifest.BuildId; removed_advertisements = $removed; before_sha256 = $beforeHash;
   after_sha256 = (Get-FileHash -LiteralPath $manifestPath).Hash; completed_utc = [DateTime]::UtcNow.ToString('o');
   scope = 'Two absent-from-receipt obsolete module advertisements only. All DLLs retained unchanged.'
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $evidence 'Receipt.json')
Write-Output 'Reconciled two obsolete texture-format advertisements; original manifest and all DLLs retained.'
