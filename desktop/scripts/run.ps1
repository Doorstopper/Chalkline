param([string]$Runtime = 'E:\Chalkline\development-runtime', [string]$Project = '')
$ErrorActionPreference = 'Stop'
$launchArguments = '-m chalkline'
if ($Project) {
    $projectPath = (Resolve-Path -LiteralPath $Project).Path
    $launchArguments += ' "' + $projectPath + '"'
}
Start-Process -FilePath "$Runtime\Scripts\pythonw.exe" -ArgumentList $launchArguments -WindowStyle Normal
