import torch, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== PyTorch CUDA Check ===")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
print(f"CUDA version: {torch.version.cuda}")

print("\n=== Unsloth Check ===")
try:
    import unsloth
    print(f"Unsloth: {unsloth.__version__}")
    from unsloth import FastLanguageModel
    print("FastLanguageModel: import OK")
    print("\n=== SUCCESS ===")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Fixing torchvision/xformers ===")
import subprocess
r1 = subprocess.run("pip install torchvision --upgrade --index-url https://download.pytorch.org/whl/cu124", shell=True, capture_output=True, text=True)
print(f"torchvision install: {r1.returncode}")
r2 = subprocess.run("pip install xformers --upgrade", shell=True, capture_output=True, text=True)
print(f"xformers install: {r2.returncode}")
print("Done")