@echo off
rem M42 UI updater for Windows: double-click this file. It looks for a newer M42 UI on GitHub, shows what is new,
rem asks, and updates the app; your models, chats, projects and settings stay. Close M42 UI first.
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
"%PY%" m42\updater.py apply %*
echo.
pause
