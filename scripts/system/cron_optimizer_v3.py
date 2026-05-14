"""Tina Cron Optimizer v3 — 分散高峰期 jobs (FULL UUIDs)"""
import subprocess

MOVES = [
    # 09:00 分散
    ('4c863cbf-7606-4ebe-9d23-aaf4243e9e12', '30 8 * * 1-5',   'Tina 大腦-團隊排程 -> 08:30'),
    ('554bfa24-367f-4e9b-9f9b-1ff30e0ae9f3', '30 9 * * 1-5',   'TW ETF 分析 -> 09:30'),
    ('7f841931-5ab2-4a57-844f-86497cc82dbd', '0 10 * * 1-5',  'Leo 法人流向 -> 10:00 (keep 13,15)'),
    ('c66a23cd-28c1-4305-8544-7f36b2cd9132', '30 10 * * 1-5',  'Tina 大腦-每日思考 -> 10:30'),
    ('c93f50c4-af77-446f-820b-822d88826976', '0 11 * * 1-5',   'Tina 每日趨勢掃描 -> 11:00'),
    ('fee0c38c-b1e2-4a77-a517-fd0b7d5e1963', '30 10 * * 1-5',  'USD/TWD -> 10:30 (keep 15:00)'),
    ('a6d89b10-8d28-492d-a495-630e8d471cfa', '30 13 * * 1-5', 'Price Check -> 13:30'),
    ('3019927f-39b7-41e8-960f-f5e29aeaf922', '0 14 * * 1-5',  'Tina 推理增強 -> 14:00 (keep 20)'),
    # 16:00 分散
    ('f57996ce-e53b-4fae-af0e-6afe5215535b', '30 15 * * 1-5', 'Maggy DB收盤 -> 15:30'),
    ('facc1550-ce47-4c5a-9a3c-04720d443b7b', '30 16 * * 1-5', 'Tina DB收盤 -> 16:30'),
]

def edit_cron(job_id, new_cron):
    result = subprocess.run(
        ['npx', 'openclaw', 'cron', 'edit', job_id, '--cron', new_cron],
        capture_output=True, text=True, shell=True, encoding='utf-8', errors='replace'
    )
    return result.returncode, result.stdout[:80], result.stderr[:80]

print('Tina Cron Optimizer v3 — Distributing peak jobs')
print('=' * 50)
for job_id, new_cron, reason in MOVES:
    print(f'  {job_id[:8]}... {reason}')
    rc, out, err = edit_cron(job_id, new_cron)
    if rc == 0:
        print(f'    [OK] -> {new_cron}')
    else:
        print(f'    [FAIL] {err}')

print('Done. Run: python list_crons.py to verify.')