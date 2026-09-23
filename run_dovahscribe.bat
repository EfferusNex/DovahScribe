@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: 1. Поиск исполняемого файла Python / Pythonw
set "PYTHONW_EXE="

if exist ".venv\Scripts\pythonw.exe" (
    set "PYTHONW_EXE=.venv\Scripts\pythonw.exe"
) else if exist "..\Runtimes\Python313\pythonw.exe" (
    set "PYTHONW_EXE=..\Runtimes\Python313\pythonw.exe"
) else (
    for /f "tokens=*" %%i in ('where pythonw 2^>nul') do (
        if not defined PYTHONW_EXE set "PYTHONW_EXE=%%i"
    )
)

if not defined PYTHONW_EXE (
    echo [DovahScribe] pythonw.exe не найден в PATH или .venv!
    echo Запуск через стандартный python.exe...
    set "PYTHONW_EXE=python"
)

:: 2. Бесшумный запуск дашборда
if "%~1"=="" (
    start "" "!PYTHONW_EXE!" "app.py"
) else (
    start "" "!PYTHONW_EXE!" "app.py" "%~1"
)

