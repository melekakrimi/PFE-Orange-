@echo off
title Orange Business AI

echo.
echo ========================================
echo   Orange Business AI - Lancement
echo ========================================
echo.

REM Backend FastAPI
start "Backend API" cmd /k "cd /d %~dp0 && set PYTHONIOENCODING=utf-8 && env\Scripts\python.exe api.py"

REM Attendre 2 secondes
timeout /t 2 /nobreak >nul

REM Frontend React
start "Frontend React" cmd /k "cd /d %~dp0interface && npm run dev"

echo.
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:3000
echo.
pause
