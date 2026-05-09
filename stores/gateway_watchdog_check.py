import sys, json, time, socket, subprocess, os
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

sys.stdout.reconfigure(encoding='utf-8')

GATEWAY_HOST = '127.0.0.1'
GATEWAY_PORT = 18789
STATE_FILE = Path(__file__).parent / 'watchdog_state.json'
LOG_FILE = Path(__file__).parent / 'watchdog_log.json'

def is_gateway_alive():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((GATEWAY_HOST, GATEWAY_PORT))
        sock.close()
        return result == 0
    except:
        return False

def stop_gateway():
    try:
        output = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq node.exe', '/FO', 'CSV', '/NH'], shell=True, stderr=subprocess.DEVNULL)
        lines = output.decode('utf-8', errors='ignore').strip().split('\n')
        for line in lines:
            if 'node.exe' in line.lower():
                parts = line.split(',')
                if len(parts) >= 2:
                    pid = int(parts[1].strip('"'))
                    subprocess.run(['taskkill', '/PID', str(pid), '/F', '/T'], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def start_gateway():
    try:
        subprocess.run(['schtasks', '/Run', '/TN', 'OpenClaw Gateway'], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

# Initial check
print(f'=== Gateway Watchdog | {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
alive = is_gateway_alive()
print(f'Gateway alive: {alive}')

# Check node processes
try:
    output = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq node.exe', '/FO', 'CSV', '/NH'], shell=True, stderr=subprocess.DEVNULL)
    lines = output.decode('utf-8', errors='ignore').strip().split('\n')
    node_pids = [int(l.split(',')[1].strip('"')) for l in lines if 'node.exe' in l.lower() and len(l.split(',')) >= 2]
    print(f'Node processes: {node_pids}')
except:
    print('Could not list node processes')

# Log state
state = {'gateway_alive': alive, 'last_check': datetime.now().isoformat(), 'action': 'startup_check'}
with open(STATE_FILE, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    json.dump([state], f, ensure_ascii=False, indent=2)

if not alive:
    print('Gateway is down, attempting restart...')
    killed = stop_gateway()
    print(f'Stopped {killed}')
    time.sleep(2)
    started = start_gateway()
    print(f'Start result: {started}')
else:
    print('Gateway is running normally - watchdog ready in background')

print('Done')