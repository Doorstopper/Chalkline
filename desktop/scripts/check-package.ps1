$ErrorActionPreference = 'Stop'
$bundle = (Get-Content -Raw -LiteralPath 'E:\Chalkline\build\latest-package.txt').Trim()
$checkRoot = 'E:\Chalkline\packaged-check'
$testProcess = Start-Process -FilePath "$bundle\Chalkline.exe" -ArgumentList "--smoke --root $checkRoot" -WindowStyle Hidden -Wait -PassThru
if ($testProcess.ExitCode -ne 0) { throw "Packaged startup failed: $($testProcess.ExitCode)" }
Get-Content -LiteralPath "$checkRoot\logs\ui.log"
if (-not (Test-Path -LiteralPath "$bundle\tools\ffmpeg.exe")) { throw 'Bundled FFmpeg missing' }
if (-not (Test-Path -LiteralPath "$bundle\tools\ffprobe.exe")) { throw 'Bundled FFprobe missing' }
$browserFiles = Get-ChildItem -LiteralPath "$bundle\app" -Recurse -File | Where-Object Name -Match 'Qt6WebEngine|QtWebEngineProcess|WebView2Loader|chrome_elf'
if ($browserFiles) { throw "Unexpected browser engine binaries: $($browserFiles.Name -join ', ')" }
Write-Output 'Packaged native startup passed; bundled media tools present; no browser-engine binaries found.'
