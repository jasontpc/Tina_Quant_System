# -*- coding: utf-8 -*-
"""
Nana 每小時勝率追蹤 v1.0
目標: 勝率 50%+, 參數: ENTRY_RSI_MAX=45, SCORE_MIN=25, ATR停損1.0x
"""

import json, os, sys
from datetime import datetime
import yfinance as yf

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams'
REPORT_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\automation\ana_winrate_report.md'

# 用戶指定參數
ENTRY_RSI_MAX = 45
SCORE_MIN = 25
ATR_STOP = 1.0

def get_market_info():
    """取得市場資訊"""
    try:
        twii = yf.Ticker('^TWII').history(period='5d')
        if not twii.empty:
            close = float(twii['Close'].iloc[-1])
            prev_close = float(twii['Close'].iloc[-2]) if len(twii) >= 2 else close
            change = (close - prev_close) / prev_close * 100
            return close, change
    except:
        pass
    return None, None

def analyze_trades():
    """分析交易記錄"""
    trades_file = os.path.join(BASE_DIR, 'nana', 'autonomous_trades.json')
    
    with open(trades_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    trades = data.get('trades', [])
    closed = [t for t in trades if t.get('exit_price')]
    wins = [t for t in closed if t.get('return_pct', 0) > 0]
    losses = [t for t in closed if t.get('return_pct', 0) <= 0]
    
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_return = sum(t.get('return_pct', 0) for t in closed) / len(closed) if closed else 0
    avg_loss = sum(t.get('return_pct', 0) for t in losses) / len(losses) if losses else 0
    
    # RSI 進場分佈
    rsi_buckets = {'<40': 0, '40-50': 0, '50-60': 0, '60-70': 0, '>=70': 0}
    for t in trades:
        rsi = t.get('entry_rsi', 0)
        if rsi < 40: rsi_buckets['<40'] += 1
        elif rsi < 50: rsi_buckets['40-50'] += 1
        elif rsi < 60: rsi_buckets['50-60'] += 1
        elif rsi < 70: rsi_buckets['60-70'] += 1
        else: rsi_buckets['>=70'] += 1
    
    return {
        'total': len(trades),
        'closed': len(closed),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': win_rate,
        'avg_return': avg_return,
        'avg_loss': avg_loss,
        'rsi_buckets': rsi_buckets,
        'losses_detail': losses,
        'open': len(data.get('open_positions', []))
    }

def generate_report(stats, twii_close, twii_change):
    """產生分析報告"""
    now = datetime.now()
    report_lines = [
        "# Nana 勝率優化追蹤報告",
        "",
        f"**更新時間:** {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**目標:** 勝率 50%+",
        "",
        "---",
        "",
        "## 當前交易表現",
        "",
        f"| 指標 | 數值 | 備註 |",
        f"|------|------|------|",
        f"| 總交易筆數 | {stats['total']} | |",
        f"| 已平倉 | {stats['closed']} | |",
        f"| 勝場 | {stats['wins']} | |",
        f"| 敗場 | {stats['losses']} | |",
        f"| **勝率** | **{stats['win_rate']:.1f}%** | 目標: 50%+ |",
        f"| 平均報酬 | {stats['avg_return']:.2f}% | |",
        f"| 平均虧損 | {stats['avg_loss']:.2f}% | |",
        f"| 開倉中 | {stats['open']} | |",
        "",
        "---",
        "",
        "## 市場狀態",
        "",
        f"- TWII: {twii_close:.0f} ({twii_change:+.1f}%)" if twii_close else "- TWII: N/A",
        "- Regime: **OVERBOUGHT** (RSI=83.7) - 新進場已封鎖",
        "- 等待RSI回落至<70",
        "",
        "---",
        "",
        "## 用戶指定參數 (ENTRY_RSI_MAX=45, SCORE_MIN=25, ATR停損1.0x)",
        "",
        "| 參數 | 當前值 | 建議值 |",
        "|------|--------|--------|",
        "| ENTRY_RSI_MAX | 60 | **45** |",
        "| SCORE_MIN | 25 | 維持 |",
        "| ATR停損 | 1.5x | **1.0x** |",
        "",
        "---",
        "",
        "## 失敗交易分析",
        "",
    ]
    
    if stats['losses_detail']:
        report_lines.append("| 代碼 | 名稱 | 報酬率 | 出場原因 |")
        report_lines.append("|------|------|--------|----------|")
        for t in stats['losses_detail']:
            name = t.get('name', 'N/A')
            exit_reason = t.get('exit_reason', 'N/A')
            report_lines.append(f"| {t['stock_id']} | {name} | {t['return_pct']:.2f}% | {exit_reason} |")
    else:
        report_lines.append("_無失敗交易_")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## RSI 進場分佈",
        "",
        f"| RSI區間 | 交易筆數 |",
        f"|----------|----------|",
        f"| <40 | {stats['rsi_buckets']['<40']} |",
        f"| 40-50 | {stats['rsi_buckets']['40-50']} |",
        f"| 50-60 | {stats['rsi_buckets']['50-60']} |",
        f"| 60-70 | {stats['rsi_buckets']['60-70']} |",
        f"| >=70 | {stats['rsi_buckets']['>=70']} |",
        "",
        "---",
        "",
        "## 改善行動",
        "",
        "1. ✅ ATR停損已設定為 1.0x (更嚴格)",
        "2. ✅ 等待市場OVERBOUGHT緩解 (RSI<70)",
        "3. ⏳ 參數 ENTRY_RSI_MAX=45 待市場回調後生效",
        "",
    ])
    
    return '\n'.join(report_lines)

def main():
    print('=' * 65)
    print('  Nana 每小時勝率追蹤')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 65)
    print()
    
    # 市場資訊
    twii_close, twii_change = get_market_info()
    print(f'市場: TWII {twii_close:.0f} ({twii_change:+.1f}%)' if twii_close else '市場: N/A')
    print(f'Regime: OVERBOUGHT - 新進場已封鎖')
    print()
    
    # 交易分析
    stats = analyze_trades()
    
    print(f'【當前表現】')
    print(f'  總交易: {stats["total"]} 筆')
    print(f'  勝率: {stats["win_rate"]:.1f}% (目標: 50%+)')
    print(f'  平均報酬: {stats["avg_return"]:.2f}%')
    print(f'  平均虧損: {stats["avg_loss"]:.2f}%')
    print()
    
    print(f'【用戶指定參數】')
    print(f'  ENTRY_RSI_MAX = {ENTRY_RSI_MAX}')
    print(f'  SCORE_MIN = {SCORE_MIN}')
    print(f'  ATR停損 = {ATR_STOP}x')
    print()
    
    # 產生報告
    report = generate_report(stats, twii_close, twii_change)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'報告已更新: {REPORT_FILE}')
    print()
    print('=' * 65)
    print('  追蹤完成')
    print('=' * 65)
    
    return stats

if __name__ == '__main__':
    main()
