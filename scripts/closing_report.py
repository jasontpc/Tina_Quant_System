# -*- coding: utf-8 -*-
"""
Tina 收盤整合報告
每天 16:00 自動生成
"""
import sys, sqlite3, requests
sys.stdout.reconfigure(encoding='utf-8')

FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
TELEGRAM_TOKEN = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
TELEGRAM_CHAT = '1616824689'

today = '2026-05-05'

# ── TWII from FinMind ──────────────────────────────────────────────────────
twii_rsi = 'N/A'
try:
    r = requests.get('https://api.finmindtrade.com/api/v4/data', params={
        'dataset': 'TaiwanStockPrice',
        'data_id': 'TXF2',
        'start_date': today, 'end_date': today,
        'token': FINMIND_TOKEN
    }, timeout=10)
    if r.status_code == 200 and r.json().get('status') == 200:
        d = r.json()['data']['data']
        if d:
            twii_rsi = d[-1].get('rsi_14', 'N/A')
except:
    pass

# ── Portfolio ────────────────────────────────────────────────────────────────
positions = [
    ('2382', '廣達',    100, 319.50, 317.50),
    ('00713', '元大高息低波', 200, 53.22, 52.90),
]

lines = [
    f"📊 *Tina 收盤整合報告* | {today} 16:00",
    "=" * 40,
    f"🏛️ TWII RSI: {twii_rsi}",
    "",
    "📦 **持倉**",
]
total_pnl = 0
for code, name, qty, cost, now in positions:
    pnl = (now - cost) * qty
    pnl_pct = (now - cost) / cost * 100
    total_pnl += pnl
    sig = '+' if pnl >= 0 else ''
    lines.append(
        f"{code} {name[:4]} ×{qty} {cost:.2f}→{now:.2f} "
        f"{sig}{pnl:,.0f}({sig}{pnl_pct:.2f}%)"
    )
sig = '+' if total_pnl >= 0 else ''
lines.append(f"累計損益: {sig}{total_pnl:,.0f}")
lines.append("=" * 40)
lines.append("💡 分析僅供參考，不構成投資建議")

msg = "\n".join(lines)

# ── Send Telegram ────────────────────────────────────────────────────────────
try:
    from urllib.request import Request, urlopen
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = '{"chat_id":"' + TELEGRAM_CHAT + '","text":"' + msg.replace('"', '\\"').replace('\n', '\\n') + '","parse_mode":"Markdown"}'
    req = Request(url, data=data.encode(), headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=15) as resp:
        print('Telegram:', resp.status)
except Exception as e:
    print('Telegram error:', e)

print("報告完成")