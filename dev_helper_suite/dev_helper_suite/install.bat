@echo off
setlocal
cd /d "%~dp0"
if not "%~1"=="" if not "%~1"=="--browser" goto usage
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ is required'"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
if "%~1"=="--browser" (
    ".venv\Scripts\python.exe" -m pip install -r requirements-browser.txt
    if errorlevel 1 goto failed
    ".venv\Scripts\python.exe" -m playwright install chromium
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import tkinter; print('Tkinter available')"
if errorlevel 1 goto failed
 echo Setup complete. Run start.bat to open Developer Helpers.
exit /b 0
:usage
echo Usage: install.bat [--browser]
exit /b 2
:failed
echo Setup failed. Check the error above. Python 3.10+ with Tcl/Tk is required.
pause
exit /b 1
