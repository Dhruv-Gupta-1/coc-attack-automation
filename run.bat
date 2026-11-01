@echo off
title COC Attacker Bot
cd /d "%~dp0"

echo ====================================================
echo        ⚔️  COC ATTACKER BOT - LAUNCHER  ⚔️
echo ====================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org and check "Add to PATH".
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import cv2, numpy, mss, PIL, pyautogui, win32gui" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing missing requirements from requirements.txt...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo Starting COC Attacker Bot...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot closed with an issue. Check logs for details.
    pause
)
