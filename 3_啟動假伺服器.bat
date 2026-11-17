@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
type "server\text\banner3.txt"
if not exist "tools\.venv\Scripts\python.exe" goto nopython
"tools\.venv\Scripts\python.exe" -I "server\lobby.py"
goto done
:nopython
type "server\text\nopython.txt"
:done
type "server\text\end3.txt"
pause >nul
