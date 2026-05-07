"""Batch enable failure-alert on all key cron jobs."""
import subprocess, json

key_jobs = [
    '6263e6d0-1ca4-4f26-ae7c-626943fa0747',  # Leo v6.5 科技股波段
    '98b172e3-283d-4cfe-8531-8b8e68b61de7',  # Leo 每日Paper Trade檢討
    'faf759b4-4ee6-40ff-8152-2c552be19816',  # Nana 波段v6.4
    'f051f79e-dc9e-4d9e-9235-fde5987643d9',  # Ray DCA 市場分析
    'facc1550-ce47-4c5a-9a3c-04720d443b7b',  # Tina 每日DB收盤更新
    '618aa329-0e53-4909-9657-83b9fa844b4f',  # Tina 全團隊整合
    '1306d237-7b4e-44cb-9fa1-847593af444f',  # Tina 自動學習擴充DB
    'fac21eb2-fa54-4c1c-a2ff-f5281de43da8',  # TW AI Tech 每日分析
    'd8fe08ae-b0e8-4812-baa3-1d82f4dfe223',  # US AI Tech 每日分析
    '51016cbe-c78c-4026-87fd-42e46610293a',  # US Fund Flow 每日更新
    '56da375e-3e44-497d-9a6c-e5f6e4b49351',  # US Margin 每日分析
    'e9f8513c-02e5-4393-b047-99ed313429ba',  # Tina 市場雷達主動狩獵
    '3019927f-39b7-41e8-960f-f5e29aeaf922',  # Tina 推理增強掃描
    'a6d89b10-8d28-492d-a495-630e8d471cfa',  # Price Check 價格檢核
    '7f841931-5ab2-4a57-844f-86497cc82dbd',  # Leo 法人資金流向
]

CLI = ['node', 'C:\\Users\\USER\\AppData\\Roaming\\npm\\node_modules\\openclaw\\dist\\index.js']

results = []
for jid in key_jobs:
    result = subprocess.run(CLI + ['cron', 'edit', jid, '--failure-alert', '--failure-alert-after', '2'],
                            capture_output=True, text=True, timeout=15)
    status = 'OK' if result.returncode == 0 else 'FAIL'
    results.append((jid[:8], status))
    print(f'{status}: {jid[:8]}...')

print()
print(f'Updated: {sum(1 for _, s in results if s == "OK")}/{len(results)}')
