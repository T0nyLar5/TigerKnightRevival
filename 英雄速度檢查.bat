@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
type "server\text\probe_banner.txt"
type "server\text\probe_menu.txt"
choice /c 123456789ABCDEFGHIJ /n >nul
if errorlevel 19 goto leash
if errorlevel 18 goto preset
if errorlevel 17 goto addr
if errorlevel 16 goto factor
if errorlevel 15 goto gate
if errorlevel 14 goto rootm
if errorlevel 13 goto stuck
if errorlevel 12 goto syncscan
if errorlevel 11 goto pin
if errorlevel 10 goto speed
if errorlevel 9 goto lift
if errorlevel 8 goto coll
if errorlevel 7 goto timechk
if errorlevel 6 goto exp
if errorlevel 5 goto props
if errorlevel 4 goto watch
if errorlevel 3 goto old
if errorlevel 2 goto fix
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py"
goto end
:fix
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --fix
goto end
:watch
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --watch
goto end
:preset
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --preset
goto end
:leash
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --leash
goto end
:addr
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --addr
goto end
:factor
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --factor
goto end
:gate
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --gate
goto end
:rootm
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --rootmotion
goto end
:stuck
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --stuck
goto end
:syncscan
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --syncscan
goto end
:pin
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --pin
goto end
:speed
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --speed
goto end
:lift
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --lift
goto end
:coll
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --coll
goto end
:timechk
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --time
goto end
:exp
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --exp
goto end
:props
"tools\.venv\Scripts\python.exe" -I "tools\ue_inspect.py" --props
goto end
:old
"tools\.venv\Scripts\python.exe" -I "tools\pawn_probe.py"
:end
echo.
type "server\text\probe_end.txt"
if not "%TK_NOPAUSE%"=="1" pause >nul
