# -*- coding: utf-8 -*-
"""
PyTorch CUDA 安裝腳本 — 為 RTX 4050 安裝正確版本
"""

import subprocess, sys, os

PYTHON = sys.executable
INDEX_URL = "https://download.pytorch.org/whl/cu124"

def run_cmd(cmd, timeout=300):
    result = subprocess.run(
        cmd, shell=True, capture_output=False
    )
    return result.returncode

print("=== PyTorch CUDA 安裝 ===")
print(f"GPU: RTX 4050 (6GB) | Driver: 566.07 | CUDA: 12.7")
print(f"Python: {PYTHON}")
print()

# 測試目前狀態
print("[1] 目前狀態")
import torch
print(f"  PyTorch: {torch.__version__} ({'CUDA' if torch.cuda.is_available() else 'CPU-only'})")

# 卸載舊版
print("\n[2] 卸載 CPU 版本...")
subprocess.run(f'"{PYTHON}" -m pip uninstall torch -y', shell=True)

# 安裝 CUDA 版本
print("\n[3] 安裝 PyTorch + CUDA 12.4...")
print(f"  Index: {INDEX_URL}")
ret = subprocess.run(
    f'"{PYTHON}" -m pip install torch --index-url {INDEX_URL} --force-reinstall',
    shell=True
)

# 驗證
print("\n[4] 驗證結果...")
import importlib
import sys
if 'torch' in sys.modules:
    del sys.modules['torch']
import torch

print(f"  PyTorch: {torch.__version__}")
print(f"  CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
    print()
    print("=== ✅ 安裝成功 ===")
else:
    print()
    print("=== ❌ 仍然 CPU-only ===")
    print("嘗試 cu121: pip install torch --index-url https://download.pytorch.org/whl/cu121")
    print("或 cu118: pip install torch --index-url https://download.pytorch.org/whl/cu118")