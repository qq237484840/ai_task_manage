@echo off
rem one-click launcher for start_server.ps1 (pass through args)
chcp 65001 >nul
title AI Task Management - Server
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_server.ps1" %*
echo.
pause
