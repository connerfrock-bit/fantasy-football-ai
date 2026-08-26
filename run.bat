@echo off
REM ============================================================
REM  Fantasy Football Draft Tool - one-click launcher (Windows)
REM  Double-click this file to start the app and open it.
REM ============================================================
cd /d "%~dp0"

echo.
echo   Fantasy Football Draft Tool
echo   ---------------------------
echo   Starting local server at http://localhost:8000/
echo   Your browser will open in a moment.
echo.
echo   KEEP THIS WINDOW OPEN while you use the app.
echo   Close it (or press Ctrl+C) to stop the server.
echo.

REM Open the browser 2s later (once the server is up), without blocking.
start "" /b powershell -NoProfile -Command "Start-Sleep 2; Start-Process 'http://localhost:8000/'"

REM Start the server (this blocks until you close the window).
python -m http.server 8000

REM If python failed to start (e.g. not installed, or port 8000 busy):
echo.
echo   Server stopped. If it never started, make sure Python is installed
echo   (https://www.python.org/downloads/) and that port 8000 is free.
pause
