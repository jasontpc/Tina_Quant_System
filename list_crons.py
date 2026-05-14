import urllib.request, json, os

url = "http://127.0.0.1:18789/cron/jobs"
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        raw = resp.read()
        text = raw.decode("utf-8", errors="replace")
        jobs = json.loads(text)
except Exception as e:
    print(f"API error: {e}")
    # Fallback: read from temp file
    path = os.path.join(os.environ["TEMP"], "crons.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
        # Find the actual JSON array (skip leading garbage)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            jobs = json.loads(raw[start:end])
        else:
            print("No JSON array found")
            exit(1)
    else:
        exit(1)

print(f"Total: {len(jobs)} jobs\n")
for j in jobs:
    tid = j["id"]
    short = tid[:8]
    ts = j.get("timeoutSeconds", "?")
    ct = j.get("cronTimeoutMs", "?")
    status = j.get("lastRunStatus", "?")
    name = j["name"]
    print(f"[{short}] ts={ts}s ct={ct}ms | {status:5} | {name[:45]}")