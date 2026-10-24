@echo off
setlocal enabledelayedexpansion
title StudyPilot — Personal Exam Planning System
color 0b

:: Ensure execution from the project's root directory
cd /d "%~dp0"

echo ======================================================================
echo          StudyPilot - Your Personal Exam Planning System
echo   Ensuring complete syllabus coverage and protected revision buffers
echo ======================================================================
echo.

:: 1. Check Python existence and version
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in your PATH!
    echo.
    echo Please install Python 3.10 or higher from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Display detected Python details
for /f "tokens=*" %%v in ('python --version') do set PYTHON_VERSION=%%v
for /f "tokens=*" %%p in ('where python 2^>nul') do (
    if not defined PYTHON_PATH set PYTHON_PATH=%%p
)
echo [SYSTEM] Python Detected: %PYTHON_VERSION%
echo          Path: %PYTHON_PATH%
echo.

:: 2. Check dependencies (fast check to avoid slow reinstalls on every launch)
echo [1/3] Checking dependencies...
python -c "import fastapi, uvicorn, pydantic, httpx, pypdf" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Installing required dependencies from requirements.txt...
    python -m pip install -r requirements.txt --no-warn-script-location
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b 1
    )
) else (
    echo [OK] All core dependencies are verified.
)

:: 3. Verify SQLite database and initial syllabus data (safe, preserves existing data)
echo [2/3] Verifying local SQLite datastore...
python -c "from backend.database import init_db; init_db()"
if errorlevel 1 (
    echo [ERROR] Failed to initialize local database.
    pause
    exit /b 1
)
echo [OK] Database verified at data\studypilot.db

:: 4. Start the StudyPilot application
echo [3/3] Launching StudyPilot server...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [NOTICE] StudyPilot process exited with an error.
)

echo.
echo Server has stopped.
pause
