@echo off
REM ============================================
REM Tina Quant System - OpenClaw Gateway Starter
REM ============================================
REM 使用方式:
REM   double-click: 啟動 gateway
REM   引數 start/stop/restart/status

cd /d "%~dp0"
echo.
echo ============================================
echo  Tina Quant System - OpenClaw Gateway
echo ============================================
echo.

if "%1"=="" goto start
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="status" goto status
goto usage

:start
echo [啟動] OpenClaw Gateway...
openclaw gateway start
goto end

:stop
echo [停止] OpenClaw Gateway...
openclaw gateway stop
goto end

:restart
echo [重啟] OpenClaw Gateway...
openclaw gateway restart
goto end

:status
echo [狀態] OpenClaw Gateway...
openclaw gateway status
goto end

:usage
echo 用法: openclaw_gateway.bat [start^|stop^|restart^|status]
echo.
echo   start   - 啟動 gateway
echo   stop    - 停止 gateway
echo   restart - 重啟 gateway
echo   status  - 顯示狀態
echo.
goto end

:end
echo.
pause