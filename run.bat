@echo off
rem Run PS2-VMC-GUI with virtual environment
rem Automatically creates venv and installs dependencies if needed.

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "GUI_SCRIPT=%SCRIPT_DIR%vmc_gui.py"

if not exist "%VENV_DIR%" (
    echo ❌ Virtual environment not found at: %VENV_DIR%
    echo.
    echo Creating virtual environment...
    if exist "%PYTHONHOME%" (
        "%PYTHONHOME%\python.exe" -m venv "%VENV_DIR%"
    ) else if exist "%SystemRoot%\py.exe" (
        "%SystemRoot%\py.exe" -m venv "%VENV_DIR%"
    ) else (
        python -m venv "%VENV_DIR%"
    )

    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        exit /b 1
    )

    echo ✅ Virtual environment created
    echo.
    echo Installing dependencies...
    call "%VENV_DIR%\Scripts\activate.bat"
    python -m pip install --upgrade pip
    python -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        exit /b 1
    )
    echo ✅ Dependencies installed
)

if not exist "%GUI_SCRIPT%" (
    echo ❌ GUI script not found at: %GUI_SCRIPT%
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"
python "%GUI_SCRIPT%"
endlocal
