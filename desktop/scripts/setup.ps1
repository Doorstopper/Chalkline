param(
    [string]$Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    [string]$Runtime = 'E:\Chalkline\development-runtime'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:TEMP = 'E:\Chalkline\temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
if (-not (Test-Path -LiteralPath "$Runtime\Scripts\python.exe")) {
    & $Python -m venv $Runtime
    if ($LASTEXITCODE -ne 0) { throw 'Could not create development environment' }
}
& "$Runtime\Scripts\python.exe" -m pip install --no-cache-dir -c "$projectRoot\requirements-build.txt" -e "$projectRoot[build]"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& "$Runtime\Scripts\python.exe" -m pip freeze
