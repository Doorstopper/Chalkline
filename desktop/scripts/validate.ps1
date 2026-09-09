param([string]$Runtime = 'E:\Chalkline\development-runtime', [switch]$Media)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = "$Runtime\Scripts\python.exe"
$env:PYTHONPYCACHEPREFIX = 'E:\Chalkline\cache\python'
& $pythonExe -m unittest discover -s "$projectRoot\tests" -p 'test_*.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Core tests failed' }
$env:QT_QPA_PLATFORM = 'offscreen'
$env:QT_QUICK_BACKEND = 'software'
& $pythonExe -m chalkline --smoke --root 'E:\Chalkline\prototype-check'
if ($LASTEXITCODE -ne 0) { throw 'QML smoke test failed' }
if ($Media) {
    & $pythonExe "$projectRoot\tests\verify_media.py" --root 'E:\Chalkline' --source 'E:\Chalkline\UWANFC U10B vs Floreat Athena-H264-TEST.mp4'
    if ($LASTEXITCODE -ne 0) { throw 'Native export validation failed' }
}
