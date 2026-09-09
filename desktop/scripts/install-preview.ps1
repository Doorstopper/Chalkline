$ErrorActionPreference = 'Stop'
$package = [System.IO.Path]::GetFullPath((Get-Content -Raw -LiteralPath 'E:\Chalkline\build\latest-package.txt').Trim())
$stagingRoot = [System.IO.Path]::GetFullPath('E:\Chalkline\build\packages\')
$destination = [System.IO.Path]::GetFullPath('E:\Chalkline\Native')
if (-not $package.StartsWith($stagingRoot, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Package is outside the expected staging directory' }
if ($destination -ne 'E:\Chalkline\Native') { throw 'Unexpected preview destination' }
if (Test-Path -LiteralPath $destination) { throw 'Native folder already exists. Stage an update; never overwrite user data.' }
if (-not (Test-Path -LiteralPath "$package\Chalkline.exe")) { throw 'Package executable missing' }
Move-Item -LiteralPath $package -Destination $destination
New-Item -ItemType Directory -Force -Path "$destination\projects" | Out-Null
Copy-Item -LiteralPath 'E:\Chalkline\test-results\20260908-144449\Native proof.chalkline' -Destination "$destination\projects\Native proof.chalkline"
$destination | Set-Content -Encoding utf8 -LiteralPath 'E:\Chalkline\build\latest-package.txt'
Write-Output "Native launch point: $destination\Chalkline.exe"
