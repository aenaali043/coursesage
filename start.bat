@echo off
cd /d "%~dp0"
title CourseSage - running (do not close this window)
echo ================================================
echo   CourseSage by Aena Ali
echo   Server: http://127.0.0.1:8000
echo   Keep this window open while using the app.
echo ================================================
echo.
start "" "http://127.0.0.1:8000"
python run.py serve 8000
echo.
echo Server stopped. Press any key to close.
pause >nul
