@echo off
REM stock_strategy_run.bat
REM Tina Quant System - 個股策略排程執行器
REM Usage: stock_strategy_run.bat [mode]
REM   mode=hourly  - 熱門股票即時更新（2330, 2454, D, DXCM）
REM   mode=4hour   - 主要觀察名單更新
REM   mode=daily   - 完整策略更新（預設）
REM   mode=report  - 完整更新 + Markdown 報告

cd /d "%~dp0.."
setlocal enabledelayedexpansion

set MODE=%1
if "%MODE%"=="" set MODE=daily

set PYTHON=python
set SCRIPT=scripts\stock_strategy_updater.py
set TRACKER=scripts\stock_strategy_tracker.py

echo [%date% %time%] Stock Strategy Scheduler - Mode: %MODE%

if "%MODE%"=="hourly" (
    echo [Hourly] Hot stocks update...
    %PYTHON% %SCRIPT% --stocks 2330 2454 D DXCM COIN
    exit /b
)

if "%MODE%"=="4hour" (
    echo [4-Hour] Main watchlist update...
    %PYTHON% %SCRIPT% --stocks 2330 2382 2454 2317 3034 2345 3017 3665 4961 0050 00646 00713 0056 D BMY SO DXCM COIN NET RIVN SMCI
    exit /b
)

if "%MODE%"=="report" (
    echo [Daily] Full strategy update with report...
    %PYTHON% %SCRIPT% --report
    %PYTHON% %TRACKER% --export-csv
    exit /b
)

REM default: full daily
echo [Daily] Full strategy update...
%PYTHON% %SCRIPT%

echo [%date% %time%] Done.