# Single Windows launch point. ATLAS_PYTHON can select a different Python 3.10+ runtime.
$atlasPython = $env:ATLAS_PYTHON
if (-not $atlasPython) {
    $atlasLocalPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $atlasLocalPython) {
        $atlasPython = $atlasLocalPython
    } elseif (Test-Path -LiteralPath 'E:\Chalkline\development-runtime\Scripts\python.exe') {
        $atlasPython = 'E:\Chalkline\development-runtime\Scripts\python.exe'
    } else {
        $atlasPython = 'python'
    }
}
& $atlasPython -B (Join-Path $PSScriptRoot 'coordinator.py') @args
exit $LASTEXITCODE
