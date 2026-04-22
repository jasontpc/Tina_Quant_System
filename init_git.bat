@echo off
REM Tina Quant System - Git 初始化腳本
REM 執行前請確認已安裝 Git for Windows

echo ========================================
echo Tina Quant System - Git 初始化
echo ========================================
echo.

cd /d "%~dp0"

REM Git 路徑
set GIT="C:\Program Files\Git\bin\git.exe"

REM 初始化
echo [1/4] 初始化 Git 倉庫...
%GIT% init
echo.

REM 加入檔案
echo [2/4] 添加檔案...
%GIT% add .
echo.

REM 初始提交
echo [3/4] 創建初始提交...
%GIT% commit -m "v3.12 stable - system clean 20260422"
echo.

REM 完成
echo [4/4] 完成！
echo.
echo ========================================
echo 下一步：連接到 GitHub
echo ========================================
echo.
echo 1. 在 GitHub 建立私人 Repo: Tina_Quant_System
echo 2. 執行:
echo    %GIT% remote add origin https://github.com/YOUR_USERNAME/Tina_Quant_System.git
echo    %GIT% push -u origin main
echo.
pause