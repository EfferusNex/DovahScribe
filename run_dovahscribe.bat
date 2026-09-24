@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

rem 1. Locate Python / Pythonw runtime
set "PYTHONW_EXE="

if exist ".venv\Scripts\pythonw.exe" (
    set "PYTHONW_EXE=%~dp0.venv\Scripts\pythonw.exe"
) else if exist "..\Runtimes\Python313\pythonw.exe" (
    set "PYTHONW_EXE=%~dp0..\Runtimes\Python313\pythonw.exe"
) else if exist "H:\Ai\Lain_Ai\Runtimes\Python313\pythonw.exe" (
    set "PYTHONW_EXE=H:\Ai\Lain_Ai\Runtimes\Python313\pythonw.exe"
) else (
    for /f "tokens=*" %%i in ('where pythonw 2^>nul') do (
        if not defined PYTHONW_EXE set "PYTHONW_EXE=%%i"
    )
)

if not defined PYTHONW_EXE (
    set "PYTHONW_EXE=python"
)

rem 2. Launch DovahScribe detached in background
if "%~1"=="" (
    start "" "!PYTHONW_EXE!" "%~dp0app.py"
) else (
    start "" "!PYTHONW_EXE!" "%~dp0app.py" "%~1"
)
exit /b 0
