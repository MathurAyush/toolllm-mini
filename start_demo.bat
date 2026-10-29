@echo off
rem Starts the live demo: sets up Python if needed, starts the server and
rem opens the demo page. Keep this window open while you use the page.
setlocal EnableExtensions
cd /d "%~dp0"
title ToolAgent demo server
set "HELPER=powershell -NoProfile -ExecutionPolicy Bypass -File scripts\demo_server.ps1"

echo.
echo  ToolAgent live demo
echo  ===================
echo.

rem --- Python environment ------------------------------------------------
if exist "venv\Scripts\python.exe" goto have_venv
echo Creating the Python environment in venv\ ...
python -m venv venv
if errorlevel 1 (
  echo.
  echo  Could not create the Python environment. Install Python 3.11 or newer
  echo  from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^)
  echo  and double-click start_demo.bat again.
  echo.
  pause
  exit /b 1
)
:have_venv
call "venv\Scripts\activate.bat"

python -c "import fastapi, uvicorn, dotenv, google.genai, sentence_transformers, sklearn, requests" >nul 2>&1
if not errorlevel 1 goto have_packages
echo Installing the required packages. The first time this takes a few minutes ...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo  Installing the packages failed; see the messages above.
  echo.
  pause
  exit /b 1
)
:have_packages

rem --- Model key ---------------------------------------------------------
%HELPER% -Action check-key
if errorlevel 2 (
  echo.
  echo  No .env file found in %CD%
  echo  Copy .env.example to .env, put your Gemini key after GEMINI_API_KEY=
  echo  and double-click start_demo.bat again.
  echo.
  pause
  exit /b 1
)
if errorlevel 1 (
  echo.
  echo  .env has no Gemini key. Open .env, put your key after GEMINI_API_KEY=
  echo  and double-click start_demo.bat again.
  echo.
  pause
  exit /b 1
)
echo Gemini key found in .env.

rem --- Port --------------------------------------------------------------
set "PORT="
for /f "delims=" %%P in ('%HELPER% -Action free-port -Port 8000') do set "PORT=%%P"
if not defined PORT (
  echo.
  echo  Could not find a free port for the server.
  echo.
  pause
  exit /b 1
)
echo Using port %PORT%.

rem --- Server ------------------------------------------------------------
start "" /b %HELPER% -Action open -Port %PORT%
echo.
echo  Starting the server at http://localhost:%PORT%/demo.html
echo  The page opens by itself once the server is ready.
echo  Keep this window open. To stop: close it, press Ctrl+C, or run stop_demo.bat.
echo.
python -m uvicorn server.app:app --port %PORT%

echo.
echo  The server has stopped.
pause
