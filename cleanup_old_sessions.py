# -*- coding: utf-8 -*-
"""Session cleanup: archive old sessions (pre-2026-05-13), keep recent."""
import os, shutil, sys
from datetime import datetime

SESSIONS_DIR = r"C:\Users\USER\.openclaw\agents\ray\sessions"
ARCHIVE_DIR = r"C:\Users\USER\.openclaw\agents\ray\archive\old_sessions"
os.makedirs(ARCHIVE_DIR, exist_ok=True)

today = "2026-05-13"
today_dt = datetime.strptime(today, "%Y-%m-%d")

kept = []
archived = []

for f in os.listdir(SESSIONS_DIR):
    if not f.endswith(".jsonl") and not f.endswith(".trajectory-path.json"):
        continue
    fpath = os.path.join(SESSIONS_DIR, f)
    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
    if mtime.date() < today_dt.date():
        # Archive old sessions
        dst = os.path.join(ARCHIVE_DIR, f)
        shutil.move(fpath, dst)
        size_mb = os.path.getsize(dst) / 1e6
        archived.append((f, round(size_mb, 1)))
    else:
        size_mb = os.path.getsize(fpath) / 1e6
        kept.append((f, round(size_mb, 1)))

total_archived_mb = sum(s for _, s in archived)
total_kept_mb = sum(s for _, s in kept)

print("=== Session Cleanup ===")
print(f"Archived {len(archived)} files ({total_archived_mb:.1f} MB):")
for f, s in archived:
    print(f"  {f} ({s} MB)")
print(f"\nKept {len(kept)} files ({total_kept_mb:.1f} MB):")
for f, s in kept:
    print(f"  {f} ({s} MB)")
print(f"\n✅ Archived {len(archived)} old session files, freed {total_archived_mb:.1f} MB")
