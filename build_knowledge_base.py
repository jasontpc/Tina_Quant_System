import os, sys

RAY_DIR = r"C:\Users\USER\.openclaw\agents\ray"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Read key files
files = {
    "AGENTS.md": "AGENTS.md",
    "SOUL.md": "SOUL.md",
    "IDENTITY.md": "IDENTITY.md",
}

print("=== Ray System Knowledge ===")
for label, fname in files.items():
    path = os.path.join(RAY_DIR, fname)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        print(f"\n--- {label} ---")
        print(content[:800])

# Scripts list
print("\n--- Ray Scripts ---")
for f in sorted(os.listdir(RAY_DIR)):
    if f.startswith("ray_") and f.endswith(".py"):
        sz = os.path.getsize(os.path.join(RAY_DIR, f)) // 1024
        print(f"  {f}: {sz}KB")