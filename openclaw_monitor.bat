@echo off
title OpenClaw Gateway Monitor
cd /d "%~dp0"
echo Starting OpenClaw Gateway Monitor...
echo This will check every 5 minutes if OpenClaw Gateway is running.
echo If not running, it will automatically restart the service.
echo.
echo Press Ctrl+C to stop the monitor.
echo.
python "%~dp0openclaw_monitor.py"
pause