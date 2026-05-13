import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
for k in ['GEMINI_API_KEY', 'GEMINI_KEY', 'GOOGLE_API_KEY']:
    v = os.environ.get(k, '')
    if v:
        print(f"{k}: set ({v[:6]}...)")
    else:
        print(f"{k}: not set")