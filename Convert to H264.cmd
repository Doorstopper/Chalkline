@echo off
setlocal
rem ---------------------------------------------------------------------------
rem Convert a match video to H.264 so Chalkline's markup exports (still / clip /
rem reel with arrows + captions) include the picture. XootGo footage is H.265,
rem which plays but can't be drawn to a canvas.
rem
rem Use it: drag a video file onto this .cmd. Or double-click it and paste a path.
rem Output is <name>-h264.mp4 next to the original. Needs ffmpeg on your PATH.
rem ---------------------------------------------------------------------------

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo ffmpeg was not found.
  echo Install it from https://ffmpeg.org/download.html , then run this again.
  pause
  exit /b 1
)

set "IN=%~1"
if "%IN%"=="" set /p "IN=Drag your match file here (or paste its path) and press Enter: "
set "IN=%IN:"=%"

if not exist "%IN%" (
  echo Could not find that file:
  echo   %IN%
  pause
  exit /b 1
)

call :mkout "%IN%"

echo Converting to H.264 — this can take a while for a full match:
echo   in:  %IN%
echo   out: %OUT%
echo.
ffmpeg -i "%IN%" -c:v libx264 -crf 20 -preset veryfast -c:a aac -b:a 160k "%OUT%"

if errorlevel 1 (
  echo.
  echo Conversion failed — see the messages above.
) else (
  echo.
  echo Done. Open this file in Chalkline instead of the original:
  echo   %OUT%
)
pause
exit /b

:mkout
rem build "<same folder>\<same name>-h264.mp4" from the input path
set "OUT=%~dpn1-h264.mp4"
goto :eof
