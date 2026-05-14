import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def jload(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return json.load(f)
    except:
        return None

BASE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
print('=== 全系統回測總覽 ===\n')

valid = []

# Tina V3 Alpha
d = jload(BASE + '\\stores\\backtest_report.json')
if d:
    t = sum(x['total_trades'] for x in d); w = sum(x['wins'] for x in d)
    pcts = []
    for x in d:
        pcts.extend([x['avg_win']]*x['wins']); pcts.extend([x['avg_loss']]*x['losses'])
    avg = sum(pcts)/len(pcts) if pcts else 0
    wr = w/t*100 if t > 0 else 0
    print('Tina V3 Alpha   US stocks/ETF            %8d %7.1f%% %+.3f%%' % (t, wr, avg))
    valid.append(('Tina', t, wr, avg))

# Nana
d = jload(BASE + '\\teams\\nana\\reports\\nana_backtest_report.json')
if d:
    perf = d.get('overall_metrics', {}); n = d.get('total_trades', 0)
    wr = perf.get('wr', 0) or 0; avg = perf.get('avg_return', 0) or 0
    print('Nana 波段      TW stocks (60檔)         %8d %7.1f%% %+.3f%%' % (n, wr, avg))
    valid.append(('Nana', n, wr, avg))

# Leo
d = jload(BASE + '\\teams\\leo\\reports\\leo_backtest_report_v2.json')
if d:
    perf = d.get('performance', {}); n = perf.get('total_trades', 0)
    wr = perf.get('win_rate', 0) or 0; avg = perf.get('avg_return', 0) or 0
    print('Leo 台股波段    TW AI tech (7檔)          %8d %7.1f%% %+.3f%%' % (n, wr, avg))
    valid.append(('Leo', n, wr, avg))

# Maggy
d = jload(BASE + '\\teams\\maggy\\reports\\full_backtest.json')
if d:
    results = d.get('results', [])
    if results:
        t = sum(r.get('total_trades',0) for r in results)
        w = sum(r.get('wins',0) for r in results)
        wr = w/t*100 if t > 0 else 0
        print('Maggy 美股      US momentum             %8d %7.1f%%      N/A' % (t, wr))
        valid.append(('Maggy', t, wr, None))

# Ray ETF
d = jload(BASE + '\\teams\\ray\\reports\\backtest_report.json')
if d and isinstance(d, dict):
    t = sum(v.get('total_trades',0) for v in d.values())
    w = sum(v.get('wins',0) for v in d.values())
    wr = w/t*100 if t > 0 else 0
    print('Ray ETF         TW/US ETF               %8d %7.1f%%      N/A' % (t, wr))
    valid.append(('Ray', t, wr, None))

# Nana Archive
d = jload(BASE + '\\teams\\nana\\archive_json\\expanded_backtest.json')
if d and isinstance(d, list) and len(d) > 0:
    t = len(d)
    wins = sum(1 for x in d if isinstance(x, dict) and x.get('pnl_pct', 0) > 0)
    pcts = [x.get('pnl_pct', 0) for x in d if isinstance(x, dict)]
    avg = sum(pcts)/len(pcts) if pcts else 0
    wr = wins/t*100 if t > 0 else 0
    print('Nana Archive    TW stocks (hist)         %8d %7.1f%% %+.3f%%' % (t, wr, avg))
    valid.append(('Nana Archive', t, wr, avg))

print('')
total_t = sum(v[1] for v in valid)
total_w = sum(v[1]*v[2]/100 for v in valid)
print('=== Summary ===')
print('有效系統: %d 個 | 總交易: %d 筆 | 加權勝率: %.1f%%' % (len(valid), total_t, total_w/total_t*100 if total_t > 0 else 0))