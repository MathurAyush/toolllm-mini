@echo off
rem Stops the demo server started by start_demo.bat.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\demo_server.ps1 -Action stop
rem Leave the message on screen for a moment.
ping -n 4 127.0.0.1 >nul
