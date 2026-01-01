@echo off
echo =====================================
echo NIFTY Replay Tool - Quick Setup
echo =====================================
echo.

:: DIRECT APPROACH - No Python detection
echo IMPORTANT: This script requires Python to be installed already.
echo If Python is NOT installed, we'll help you install it.
echo.

:: Quick check - is python command working?
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    goto :python_ready
)

echo Python is NOT in PATH or not installed.
echo.
echo You need to install Python first:
echo 1. Download from https://python.org
echo 2. Run installer
echo 3. CHECK "Add Python to PATH" (very important!)
echo 4. Complete installation
echo.
echo Opening Python download page...
start https://www.python.org/downloads/windows/
echo.
echo After installing Python, close ALL terminals and re-run this script.
echo.
pause
exit /b 1

:python_ready
:: Show Python version
python --version
echo.

:: Install requirements
echo Installing/upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing requirements from requirements.txt...
if exist requirements.txt (
    python -m pip install -r requirements.txt
) else (
    echo ERROR: requirements.txt not found!
    echo.
    echo Files in this folder:
    dir /b
    echo.
    pause
    exit /b 1
)

echo.
:: Run the tool
echo Starting NIFTY Replay Tool...
if exist Replay_Tool.py (
    python Replay_Tool.py
) else (
    echo ERROR: Replay_Tool.py not found!
    echo.
    echo Python files in this folder:
    dir /b *.py
    echo.
    echo If your main file has a different name, rename it to Replay_Tool.py
)

echo.
pause