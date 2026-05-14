@echo off
setlocal enabledelayedexpansion
title Offline File Organiser Agent - Windows Build

echo.
echo  ============================================================
echo   OFFLINE FILE ORGANISER AGENT - WINDOWS BUILD SCRIPT
echo  ============================================================
echo.

set PYTHON=
for %%P in (python python3 py) do (
    if not defined PYTHON (
        %%P --version >nul 2>&1
        if not errorlevel 1 set PYTHON=%%P
    )
)

if not defined PYTHON (
    for %%D in (
        "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
        "%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe"
        "%LOCALAPPDATA%\Python\pythoncore-3.12-64\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "C:\Python314\python.exe"
        "C:\Python313\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
    ) do (
        if not defined PYTHON (
            if exist %%D set PYTHON=%%~D
        )
    )
)

if not defined PYTHON (
    echo  [ERROR] Python not found.
    echo  Install Python 3.10+ from python.org and tick "Add Python to PATH".
    pause
    exit /b 1
)

echo  [OK] Using Python: %PYTHON%
"%PYTHON%" --version

echo.
"%PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo  [INFO] PyInstaller not found. Installing...
    "%PYTHON%" -m pip install pyinstaller --upgrade --quiet
    if errorlevel 1 (
        echo  [ERROR] Could not install PyInstaller.
        pause
        exit /b 1
    )
)
echo  [OK] PyInstaller ready.

set SCRIPT_DIR=%~dp0
if "%SCRIPT_DIR:~-1%"=="\" set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

set SRC=%SCRIPT_DIR%\src\file_organiser_agent.py
set OUT=%SCRIPT_DIR%\dist\windows
set BUILD=%SCRIPT_DIR%\build\windows
set ICON=%SCRIPT_DIR%\assets\app.ico

if not exist "%SRC%" (
    echo  [ERROR] Cannot find: %SRC%
    pause
    exit /b 1
)

mkdir "%OUT%" >nul 2>&1
mkdir "%BUILD%" >nul 2>&1

echo.
echo  ============================================================
echo   BUILDING SINGLE EXE
echo  ============================================================
echo.

if exist "%ICON%" (
    "%PYTHON%" -m PyInstaller ^
        --noconfirm ^
        --onefile ^
        --windowed ^
        --name "Offline-File-Organiser-Agent" ^
        --distpath "%OUT%" ^
        --workpath "%BUILD%" ^
        --specpath "%BUILD%" ^
        --icon "%ICON%" ^
        "%SRC%"
) else (
    "%PYTHON%" -m PyInstaller ^
        --noconfirm ^
        --onefile ^
        --windowed ^
        --name "Offline-File-Organiser-Agent" ^
        --distpath "%OUT%" ^
        --workpath "%BUILD%" ^
        --specpath "%BUILD%" ^
        "%SRC%"
)

if errorlevel 1 (
    echo.
    echo  ============================================================
    echo   BUILD FAILED
    echo  ============================================================
    pause
    exit /b 1
)

set EXE=%OUT%\Offline-File-Organiser-Agent.exe
if not exist "%EXE%" (
    echo  [ERROR] Build finished but EXE not found.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   SUCCESS
echo  ============================================================
echo.
echo   Standalone EXE: %EXE%
echo.
pause
