import urllib.request, os, sys

HF_TOKEN = os.getenv("HF_TOKEN", "")
MODEL_URL = "https://huggingface.co/bartowski/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
DEST_PATH = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'Ollama', 'models', 'qwen35-4b-iq4xs', 'Qwen3.5-4B-IQ4_XS.gguf')

existing = os.path.getsize(DEST_PATH) if os.path.exists(DEST_PATH) else 0
print(f"Current file: {existing:,} bytes ({existing//1024//1024} MB)")

req = urllib.request.Request(MODEL_URL)
if HF_TOKEN:
    req.add_header('Authorization', f'Bearer {HF_TOKEN}')
req.add_header('User-Agent', 'Mozilla/5.0')
if existing:
    req.add_header('Range', f'bytes={existing}-')

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        cl = resp.headers.get('Content-Length', '0')
        total = int(cl) + existing if existing else 0
        print(f"Resume from byte {existing:,} | Total expected: {total:,} bytes ({total//1024//1024} MB)")
        mode = 'ab' if existing else 'wb'
        with open(DEST_PATH, mode) as f:
            downloaded = existing
            while True:
                chunk = resp.read(2*1024*1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded/total*100
                    print(f"\r  {downloaded:,}/{total:,} bytes ({pct:.1f}%)", end='', flush=True)
                else:
                    print(f"\r  {downloaded:,} bytes", end='', flush=True)
        print("\nDone!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
