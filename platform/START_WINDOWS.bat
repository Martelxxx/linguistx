@echo off
setlocal
cd /d "%~dp0.."
echo Linguist-X AES67 shared gateway - Windows lab
where py >nul 2>&1
if errorlevel 1 (echo Python 3.11+ launcher is required & exit /b 1)
if not exist ".venv-shared\Scripts\python.exe" py -3 -m venv .venv-shared
if errorlevel 1 exit /b 1
call ".venv-shared\Scripts\python.exe" -m pip install -r gateway_stage2\requirements.txt
if errorlevel 1 exit /b 1
echo Install the GStreamer Windows Runtime from gstreamer.freedesktop.org and set LX_GSTREAMER_BIN if it is not on PATH.
".venv-shared\Scripts\python.exe" -m gateway_stage2.launch_shared
