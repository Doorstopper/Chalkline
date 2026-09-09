param([string]$Runtime = 'E:\Chalkline\development-runtime')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$buildRoot = 'E:\Chalkline\build'
# Build into a fresh staging directory. Never let PyInstaller --noconfirm erase a
# previously launched portable folder containing projects, settings or exports.
$distRoot = Join-Path $buildRoot ('packages\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$env:PYINSTALLER_CONFIG_DIR = "$buildRoot\cache"
$env:TEMP = 'E:\Chalkline\temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $buildRoot,$env:TEMP | Out-Null
& "$Runtime\Scripts\python.exe" -m PyInstaller --noconfirm --onedir --windowed --name Chalkline --contents-directory app --collect-data chalkline --additional-hooks-dir "$projectRoot\packaging\hooks" --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtWebEngineQuick --distpath $distRoot --workpath "$buildRoot\work" --specpath $buildRoot "$projectRoot\packaging\entry.py"
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
$bundle = "$distRoot\Chalkline"
New-Item -ItemType Directory -Force -Path "$bundle\tools","$bundle\licenses" | Out-Null
foreach ($toolName in @('ffmpeg','ffprobe')) {
    $source = (Get-Command $toolName -ErrorAction Stop).Source
    Copy-Item -LiteralPath $source -Destination "$bundle\tools\$toolName.exe"
}
$licenseProcess = Start-Process -FilePath "$bundle\tools\ffmpeg.exe" -ArgumentList '-L' -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$bundle\licenses\ffmpeg-license.txt" -RedirectStandardError "$bundle\licenses\ffmpeg-build.txt"
if ($licenseProcess.ExitCode -ne 0) { throw 'Could not record FFmpeg build information' }
Copy-Item -LiteralPath "$projectRoot\README.md" -Destination "$bundle\README.md"
Copy-Item -LiteralPath "$projectRoot\docs\parity.md" -Destination "$bundle\FEATURE-STATUS.md"
$bundle | Set-Content -Encoding utf8 -LiteralPath "$buildRoot\latest-package.txt"
Write-Output "Portable prototype: $bundle\Chalkline.exe"
