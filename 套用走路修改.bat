@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight\KingdomGame\CookedPC\KingdomGame.u"
set "BAKDIR=%~dp0server\mods\backup"
set "BAK=%~dp0server\mods\backup\KingdomGame.u"
set "ORIGSIZE=156001509"
set "ORIGSHA=75bb7a42ffb40db005b8c1650fe8c32e845896c522733396bed558b88e6b4f90"
type "server\text\mod_banner.txt"
if not exist "%GAME%" goto nogame
tasklist /FI "IMAGENAME eq Kingdom-Win64-Shipping.exe" | find /I "Kingdom-Win64" >nul
if not errorlevel 1 goto running
set "PICK=%~1"
if not "%PICK%"=="" goto picked
type "server\text\mod_menu.txt"
choice /c ADE /n >nul
if errorlevel 3 goto pickE
if errorlevel 2 goto pickD
set "PICK=A"
goto picked
:pickD
set "PICK=D_diag"
goto picked
:pickE
set "PICK=E"
:picked
if /i "%PICK%"=="D" set "PICK=D_diag"
set "MOD=%~dp0server\mods\KingdomGame_%PICK%.u"
if not exist "%MOD%" goto nomod
if exist "%BAK%" goto havebak
for %%I in ("%GAME%") do set "GSIZE=%%~zI"
if not "%GSIZE%"=="%ORIGSIZE%" goto notorig
certutil -hashfile "%GAME%" SHA256 | find /I "%ORIGSHA%" >nul
if errorlevel 1 goto notorig
if not exist "%BAKDIR%" mkdir "%BAKDIR%"
copy /y "%GAME%" "%BAK%" >nul
fc /b "%GAME%" "%BAK%" >nul
if errorlevel 1 goto bakfail
goto docopy
:havebak
for %%I in ("%BAK%") do set "BSIZE=%%~zI"
if not "%BSIZE%"=="%ORIGSIZE%" goto bakbad
certutil -hashfile "%BAK%" SHA256 | find /I "%ORIGSHA%" >nul
if errorlevel 1 goto bakbad
:docopy
copy /y "%MOD%" "%GAME%" >nul
if errorlevel 1 goto copyfail
fc /b "%MOD%" "%GAME%" >nul
if errorlevel 1 goto copyfail
echo.
echo   [%PICK%]
type "server\text\mod_done.txt"
goto end
:nogame
type "server\text\mod_nogame.txt"
goto end
:nomod
type "server\text\mod_nomod.txt"
goto end
:running
type "server\text\mod_running.txt"
goto end
:notorig
type "server\text\mod_notorig.txt"
goto end
:bakbad
type "server\text\mod_bakbad.txt"
goto end
:bakfail
type "server\text\mod_bakfail.txt"
goto end
:copyfail
type "server\text\mod_copyfail.txt"
:end
if not "%TK_NOPAUSE%"=="1" pause >nul
