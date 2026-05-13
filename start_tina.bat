@echo off
:: Ray Tina 環境啟動腳本
:: Ollama + Qwen2.5 本地模型 for i9-13900H + RTX 4050 Laptop

echo [*] Ray Tina Engine Starting...
echo [*] i9-13900H + RTX 4050 Laptop Configuration

:: RTX 4050 記憶體管理：單一模型加載，避免 6GB 溢出
set OLLAMA_NUM_PARALLEL=4
:: 模型常駐 24 小時，減少重複載入
set OLLAMA_KEEP_ALIVE=24h
:: 限制同時加載模型數
set OLLAMA_MAX_LOADED_MODELS=1
:: 使用 CPU 運算（i9 強大單核）
set OLLAMA_GPU_OVERHEAD=0

:: 啟動 Ollama 服務（維持在背景）
echo [*] Starting Ollama service...
start "Ollama" cmd /c "ollama serve"
timeout /t 3 /nobreak >nul

:: 檢查服務是否啟動
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ollama service failed to start. Try running 'ollama serve' manually.
) else (
    echo [OK] Ollama service running on http://localhost:11434
)

echo [*] Loading Qwen2.5 models...
echo [*] Tip: Run 'ollama run qwen2.5:1.5b' for fast logic, 'ollama run qwen2.5:7b' for deep analysis
echo.
echo Available models after loading:
ollama list
echo.
echo Done. OpenClaw can now use tina_bridge.py to call local Qwen models.
pause