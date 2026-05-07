# Full health check - step 1: cron status
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
cli = r"C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js"
out = subprocess.run(["node", cli, "cron", "list"], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=25).stdout
lines = out.splitlines()
crons = {}
error_ids = []
for line in lines:
    if len(line) > 35 and line[0] not in (' ', '\t', ' '):
        parts = line.split()
        if len(parts) >= 2:
            cid = parts[0]
            name = " ".join(parts[1:])
            crons[cid] = {'name': name, 'status': 'unknown'}
for line in lines:
    for cid in crons:
        if cid in line:
            s = 'error' if 'error' in line.lower() else ('ok' if 'ok' in line.lower() else ('idle' if 'idle' in line.lower() else ('running' if 'running' in line.lower() else 'unknown')))
            crons[cid]['status'] = s
ok = [c for c,v in crons.items() if v['status']=='ok']
err = [c for c,v in crons.items() if v['status']=='error']
run_ = [c for c,v in crons.items() if v['status']=='running']
idle = [c for c,v in crons.items() if v['status']=='idle']
print(f"Cron: total={len(crons)} ok={len(ok)} error={len(err)} running={len(run_)} idle={len(idle)}")
for cid, v in crons.items():
    if v['status'] == 'error':
        # Check timeout
        detail = subprocess.run(["node", cli, "cron", "show", cid], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15).stdout
        tout = next((l for l in detail.splitlines() if 'timeoutSeconds' in l), '')
        print(f"  🔴 {v['name']}: {tout.strip()[:60]}")
print("Done")