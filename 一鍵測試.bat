@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
type "server\text\oneclick_banner.txt"
if not exist "tools\.venv\Scripts\python.exe" goto nopython
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\stop_servers.ps1"
start "TK-lobby" cmd /c ""tools\.venv\Scripts\python.exe" -I "server\lobby.py" & pause"
start "TK-battle" cmd /c ""tools\.venv\Scripts\python.exe" -I "server\battle_server.py" & pause"
type "server\text\oneclick_steps.txt"
goto done
:nopython
type "server\text\nopython.txt"
:done
if not "%TK_NOPAUSE%"=="1" pause >nul
