@echo off
setlocal
cd /d "%~dp0"
title The Autonomous Digital Circus

if not exist ".venv\Scripts\python.exe" (
    echo Setting up the Autonomous AI World for the first time...
    py -3 -m venv .venv 2>nul
    if errorlevel 1 python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo Python 3.11 or newer is required. Install Python, then double-click this file again.
    pause
    exit /b 1
)

echo Preparing the web world...
".venv\Scripts\python.exe" -m pip install -e . --disable-pip-version-check -q
if errorlevel 1 (
    echo Setup could not download the required web packages. Check your internet connection.
    pause
    exit /b 1
)

echo Starting the world. Your browser will open automatically.
echo Keep this window open while you watch. Press Ctrl+C here to stop.
".venv\Scripts\python.exe" -m autonomous_ai_world.web_server
if errorlevel 1 pause
