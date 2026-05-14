@echo off
REM ============================================================
REM Ray System 2.0 — US AI Dashboard Launcher
REM ============================================================
cd /d C:\Users\USER\.openclaw\workspace\Tina_Quant_System

setlocal enabledelayedexpansion
set ARGS=%*
if "!ARGS!"=="" set ARGS=--debug --log

echo Starting Ray System 2.0 US Dashboard...
echo Arguments: !ARGS!
echo.
echo URL: http://localhost:8501
echo Press Ctrl+C to stop
echo.
streamlit run ray_us_dashboard.py --server.port 8501 --browser.gatherUsageStats false -- !ARGS!

REM Usage:
REM   run_ray_dashboard.bat              # DEBUG + LOG 預設
REM   run_ray_dashboard.bat --debug       # 只有 DEBUG
REM   run_ray_dashboard.bat --log         # 只有 LOG
REM   run_ray_dashboard.bat --debug --log # 兩者皆開
REM   run_ray_dashboard.bat --help        # 顯示說明