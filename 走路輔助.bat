@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
net session >nul 2>&1
if errorlevel 1 goto elevate
type "server\text\walkhelper_banner.txt"
if not exist "tools\.venv\Scripts\python.exe" goto nopython
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --walkhelper
goto end
:elevate
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b
:nopython
type "server\text\nopython.txt"
:end
if not "%TK_NOPAUSE%"=="1" pause >nul
