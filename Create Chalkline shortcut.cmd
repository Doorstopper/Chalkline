@echo off
setlocal
rem Creates a Desktop shortcut that opens the LOCAL Chalkline app -- the
rem index.html next to this script -- in your default browser. No server and no
rem internet are needed: the service worker skips registering on file:// URLs,
rem so index.html runs fine straight off disk. Run this from the repo folder.

set "APP=%~dp0index.html"

if not exist "%APP%" (
  echo Could not find index.html next to this script.
  echo Move this file into the Chalkline repo folder and run it again.
  pause
  exit /b 1
)

rem Resolve the real Desktop via Windows itself, so this works even when the
rem Desktop is redirected to OneDrive (where %USERPROFILE%\Desktop does not exist).
for /f "delims=" %%D in ('powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"') do set "DESK=%%D"

if not defined DESK (
  echo Could not locate your Desktop folder.
  pause
  exit /b 1
)

set "LINK=%DESK%\Chalkline.url"

> "%LINK%" echo [InternetShortcut]
>> "%LINK%" echo URL=file:///%APP:\=/%
>> "%LINK%" echo IconFile=%~dp0chalkline.ico
>> "%LINK%" echo IconIndex=0

echo Created shortcut: %LINK%
echo It opens:         %APP%
echo.
echo Double-click "Chalkline" on your Desktop to launch the local app.
pause
