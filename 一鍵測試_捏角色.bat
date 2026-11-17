@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set TK_NEW_CHAR=1
type "server\text\newchar_banner.txt"
if not exist "tools\.venv\Scripts\python.exe" goto nopython
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\stop_servers.ps1"
start "TK-lobby-newchar" cmd /c ""tools\.venv\Scripts\python.exe" -I "server\lobby.py" & pause"
goto done
:nopython
type "server\text\nopython.txt"
:done
if not "%TK_NOPAUSE%"=="1" pause >nul
