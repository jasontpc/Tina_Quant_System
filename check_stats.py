import json, os

print('=== 三大團隊勝率與交易數量 ===')
print()

# Nana
p = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\ana_sim_trades.json'
if os.path.exists(p):
    with open(p, encoding='utf-8') as f:
        d = json.load(f)
    trades = d.get('trades', [])
    wins = [t for t in trades if t.get('return_pct', 0) > 0]
    print('【Nana 波段 v6.4】')
    print('  總交易:', len(trades), '筆')
    if trades:
        wr = len(wins)/len(trades)*100
        avg = sum(t['return_pct'] for t in trades)/len(trades)
        print('  勝率: {:.1f}%'.format(wr))
        print('  平均報酬: {:.3f}%'.format(avg))
else:
    print('【Nana】無交易資料')

print()

# Leo
p2 = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'
if os.path.exists(p2):
    with open(p2, encoding='utf-8') as f:
        d = json.load(f)
    trades = d.get('trades', [])
    wins = [t for t in trades if t.get('pnl', 0) > 0]
    print('【Leo 科技股 v6.5】')
    print('  總交易:', len(trades), '筆')
    if trades:
        wr = len(wins)/len(trades)*100
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        print('  勝率: {:.1f}%'.format(wr))
        print('  總損益: NT${:,.0f}'.format(total_pnl))
else:
    print('【Leo】無交易資料')

print()
print('=== Grid Search / WFA 最優化結果 ===')

# Nana Grid Search
p3 = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\best_params.json'
if os.path.exists(p3):
    with open(p3, encoding='utf-8') as f:
        d = json.load(f)
    bc = d.get('best_config', {})
    br = d.get('backtest_result', {})
    print('NANA GRID: WR={:.1f}% | 交易={}筆 | Avg={:+.2f}%'.format(
        br.get('win_rate', 0), br.get('total_trades', 0), br.get('avg_return', 0)))

# Leo Matrix WFA
p4 = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\matrix_results\best_leo_params.json'
if os.path.exists(p4):
    with open(p4, encoding='utf-8') as f:
        d = json.load(f)
    print('LEO WFA: WR={:.1f}% | Val Sharpe={:.2f} | Score={:.2f}'.format(
        d.get('val_wr', 0), d.get('val_sharpe', 0), d.get('score', 0)))
    bc = d.get('best_config', {})
    print('  參數: RSI_P={} Thresh={} Hold={}d TP={}% SL={}%'.format(
        bc.get('rsi_period', ''), bc.get('rsi_threshold', ''),
        bc.get('hold_days', ''), bc.get('tp_pct', ''), bc.get('sl_pct', '')))

# Leo Grid Search
p5 = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\best_params.json'
if os.path.exists(p5):
    with open(p5, encoding='utf-8') as f:
        d = json.load(f)
    bc = d.get('best_config', {})
    br = d.get('backtest_result', {})
    print('LEO GRID: WR={:.1f}% | 交易={}筆 | Avg={:+.2f}%'.format(
        br.get('win_rate', 0), br.get('total_trades', 0), br.get('avg_return', 0)))