@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight\KingdomGame\CookedPC\KingdomGame.u"
set "BAK=%~dp0server\mods\backup\KingdomGame.u"
type "server\text\restore_banner.txt"
if not exist "%BAK%" goto nobak
tasklist /FI "IMAGENAME eq Kingdom-Win64-Shipping.exe" | find /I "Kingdom-Win64" >nul
if not errorlevel 1 goto running
copy /y "%BAK%" "%GAME%" >nul
if errorlevel 1 goto fail
fc /b "%BAK%" "%GAME%" >nul
if errorlevel 1 goto fail
type "server\text\restore_done.txt"
goto end
:nobak
type "server\text\restore_nobak.txt"
goto end
:running
type "server\text\mod_running.txt"
goto end
:fail
type "server\text\restore_fail.txt"
:end
if not "%TK_NOPAUSE%"=="1" pause >nul
