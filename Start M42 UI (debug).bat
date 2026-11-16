@echo off
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if "%PY%"=="python" where python >nul 2>nul || (
  echo Python not found. Run install.bat first.
  pause
  exit /b 1
)
"%PY%" m42\app.py %*
if errorlevel 1 pause
