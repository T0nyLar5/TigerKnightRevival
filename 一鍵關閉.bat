@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\stop_servers.ps1" -Game
type "server\text\stop_done.txt"
if not "%TK_NOPAUSE%"=="1" pause >nul
