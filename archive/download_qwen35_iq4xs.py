import urllib.request, os

HF_TOKEN = os.getenv("HF_TOKEN", "")
MODEL_URL = "https://huggingface.co/bartowski/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
DEST_PATH = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'Ollama', 'models', 'qwen35-4b-iq4xs', 'Qwen3.5-4B-IQ4_XS.gguf')

req = urllib.request.Request(MODEL_URL)
if HF_TOKEN:
    req.add_header('Authorization', f'Bearer {HF_TOKEN}')
req.add_header('User-Agent', 'Mozilla/5.0')

existing = 0
if os.path.exists(DEST_PATH):
    existing = os.path.getsize(DEST_PATH)
    req.add_header('Range', f'bytes={existing}-')

print(f"Starting download from byte {existing}")
print(f"URL: {MODEL_URL}")

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = resp.headers.get('Content-Length', 0)
        print(f"Total size: {total} bytes")
        with open(DEST_PATH, 'ab') as f:
            downloaded = existing
            while True:
                chunk = resp.read(1024*1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded/int(total)*100
                    print(f"\r{downloaded:,}/{int(total):,} bytes ({pct:.1f}%)", end='', flush=True)
                else:
                    print(f"\r{downloaded:,} bytes", end='', flush=True)
    print("\nDownload complete!")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    print(f"Body: {e.read().decode()[:200]}")
