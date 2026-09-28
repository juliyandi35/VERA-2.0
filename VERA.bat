@echo off
setlocal
cd /d "%~dp0"

set "VERA_PYTHON=C:\Users\juliy\anaconda3\python.exe"
if not exist "%VERA_PYTHON%" set "VERA_PYTHON=python"

echo Menyalakan V.E.R.A. di http://127.0.0.1:5000 ...
start "V.E.R.A. Server" /B "%VERA_PYTHON%" app.py
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000"
endlocal
