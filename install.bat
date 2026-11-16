@echo off
rem M42 UI installer for Windows: Python, its packages (in .venv), then m42\setup.py checks this PC, picks the model
rem that fits (2B for 8 GB RAM, 4B for 16 GB or a graphics card), asks, downloads and starts the app.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
echo M42 UI installer (Windows)
echo.

set "PY="
where py >nul 2>nul && (py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3")
if not defined PY (
  where python >nul 2>nul && (python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python")
)
if not defined PY (
  echo Python 3.10 or newer was not found.
  where winget >nul 2>nul || (
    echo Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run install.bat again.
    start "" https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set /p OK=Install Python 3.12 now with winget ^(Microsoft's installer^)? [Y/n]
  if /i "!OK!"=="n" ( echo Nothing was installed. & pause & exit /b 1 )
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
  if not exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    echo Python was installed: close this window and run install.bat again.
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo Making M42 UI's own Python environment in .venv ...
  %PY% -m venv .venv || ( echo Could not make .venv & pause & exit /b 1 )
)
set "VPY=.venv\Scripts\python.exe"

echo.
echo M42 UI installs its Python packages into .venv (about 700 MB: the page tools, speech, PyTorch for the CPU).
set /p OK=Install them now? [Y/n]
if /i "%OK%"=="n" ( echo Nothing was installed. & pause & exit /b 1 )
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install -r requirements.txt || ( echo The packages did not install: see the lines above. & pause & exit /b 1 )
"%VPY%" -m pip install torch --index-url https://download.pytorch.org/whl/cpu || echo PyTorch did not install: the Tanglish speech model stays off.

echo.
"%VPY%" m42\setup.py %*
pause
