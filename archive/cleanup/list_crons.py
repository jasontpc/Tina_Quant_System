import json, subprocess

result = subprocess.run(['npx', 'openclaw', 'cron', 'list', '--json'],
                        capture_output=True, text=True, shell=True,
                        encoding='utf-8', errors='replace')
try:
    data = json.loads(result.stdout)
    for j in data.get('jobs', []):
        expr = j['schedule']['expr']
        name = j['name'][:35].encode('ascii', errors='replace').decode()
        print(f"('{j['id']}', '{expr}', '{name}')")
except Exception as e:
    print(f'Error: {e}')
    print(f'stdout len={len(result.stdout)}, returncode={result.returncode}')
    print(result.stdout[:500])