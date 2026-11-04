@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%~dp0YouTube_Enterprise_Studio.exe" (
    start "" "%~dp0YouTube_Enterprise_Studio.exe"
    exit /b 0
)
start "" pythonw "%~dp0youtube_enterprise_desktop_app.py"
exit /b 0
