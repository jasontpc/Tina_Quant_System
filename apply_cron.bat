@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0tools\apply_cron.ps1" %*