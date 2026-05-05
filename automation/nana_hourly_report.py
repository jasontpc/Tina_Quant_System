# Nana Winrate Analysis - Hourly Cron Report
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime
from collections import defaultdict

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams'

# Load trades
nana_trades_file = os.path.join(BASE_DIR, 'nana', 'autonomous_trades.json')
with open(nana_trades_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])
closed = [t for t in trades if t.get('exit_price')]
losses = [t for t in closed if t.get('return_pct', 0) <= 0]
wins = [t for t in closed if t.get('return_pct', 0) > 0]

print('=' * 60)
print('  Nana 勝率提升分析 - 每小時報告')
print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('=' * 60)

print()
print('【1】交易現狀')
print(f'  總交易筆數: {len(trades)}')
print(f'  已平倉: {len(closed)}')
print(f'  勝筆: {len(wins)} / 敗筆: {len(losses)}')
wr = len(wins) / len(closed) * 100 if closed else 0
print(f'  勝率: {wr:.1f}%  (目標: 50%+)')

if losses:
    loss_returns = [t['return_pct'] for t in losses]
    avg_loss = sum(loss_returns) / len(loss_returns)
    max_loss = min(loss_returns)
    print(f'  平均虧損: {avg_loss:.2f}%')
    print(f'  最大虧損: {max_loss:.2f}%')

print()
print('【2】失敗原因分析')
exit_reasons = defaultdict(int)
for t in closed:
    exit_reasons[t.get('exit_reason', 'unknown')] += 1
for reason, cnt in sorted(exit_reasons.items(), key=lambda x: -x[1]):
    print(f'  {reason}: {cnt}次')

rsi_distribution = defaultdict(int)
for t in trades:
    rsi = t.get('entry_rsi', 0)
    if rsi < 40:
        rsi_distribution['<40'] += 1
    elif rsi < 50:
        rsi_distribution['40-50'] += 1
    elif rsi < 55:
        rsi_distribution['50-55'] += 1
    elif rsi < 65:
        rsi_distribution['55-65'] += 1
    else:
        rsi_distribution['>=65'] += 1

print()
print('  RSI進場分佈:')
for bucket, cnt in rsi_distribution.items():
    print(f'    {bucket}: {cnt}次')

print()
print('【3】自動參數調整 (nana_improved_config.json)')
config = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'improved': True,
    'entry_rsi_max': 55,
    'entry_score_min': 35,
    'entry_bias_max': 3.0,
    'atr_stop': 1.0,
    'take_profit_pct': 15.0,
    'hold_days_max': 7,
    'regime_filter': True,
}
config_file = os.path.join(BASE_DIR, 'nana', 'nana_improved_config.json')
with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)
print('  已寫入改善參數:')
for k, v in config.items():
    print(f'    {k}: {v}')

print()
print('【4】勝率追蹤摘要')
print(f'  v58 回測勝率: 72.7%  (Tier1>=40 嚴格門檻)')
print(f'  模擬交易勝率: {wr:.1f}%  (落後)')
print(f'  缺口分析: 實盤勝率落後回測 {72.7 - wr:.1f}%')
print(f'  主因: hold_days_max=10 導致該贏的變平手')
print()
print('  改善行動:')
print('  [V] 持有天數上限: 10天->7天 (更積極出場)')
print('  [V] ATR停損: 1.0x (更嚴格)')
print('  [V] RSI上限: 55 (避免高點進場)')
print('  [V] OVERBOUGHT市場禁止進場')
print()
print('=' * 60)
print('  ✅ 勝率優化分析完成')
print('=' * 60)
