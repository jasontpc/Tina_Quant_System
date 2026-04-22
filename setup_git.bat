@echo off
REM Tina Quant System - Git Setup Script
REM Run this after installing Git for Windows

echo ========================================
echo Tina Quant System - Git 初始化
echo ========================================
echo.

cd /d "%~dp0"

REM Check if git is installed
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git 未安裝！
    echo.
    echo 請先安裝 Git for Windows:
    echo 1. 前往 https://git-scm.com/download/win
    echo 2. 下載並安裝
    echo 3. 重新執行此腳本
    pause
    exit /b 1
)

echo [OK] Git 已安裝
echo.

REM Initialize git
echo 初始化 Git 倉庫...
git init
echo.

REM Add files
echo 添加檔案...
git add .
echo.

REM Create initial commit
echo 創建初始提交...
git commit -m "v3.12 stable - system clean 20260422"
echo.

REM Set remote (需要手動替換 YOUR_USERNAME)
echo ========================================
echo 下一步：添加 GitHub Remote
echo ========================================
echo.
echo 1. 在 GitHub 建立私人 Repo: Tina_Quant_System
echo 2. 替換 YOUR_USERNAME 為你的 GitHub 用戶名
echo 3. 執行:
echo    git remote add origin https://github.com/YOUR_USERNAME/Tina_Quant_System.git
echo    git push -u origin main
echo.

pause
