# -*- coding: utf-8 -*-
"""
Ray DCA Scheduler — 自動化排程腳本
用法:
  python scripts/dca_scheduler.py weekly   # 每週 review
  python scripts/dca_scheduler.py monthly # 每月 portfolio 檢視
  python scripts/dca_scheduler.py alert  # 低價警報檢查
"""
import sys
import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Dynamic path setup: project root is parent of 'teams/'
_ScriptDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../teams/ray/scripts -> .../teams/ray -> root
if _ScriptDir not in sys.path:
    sys.path.insert(0, _ScriptDir)

try:
    from teams.team_shared import TeamShared
except ModuleNotFoundError:
    _alt = os.path.dirname(_ScriptDir)
    if _alt not in sys.path:
        sys.path.insert(0, _alt)
    import team_shared as _ts
    TeamShared = _ts.TeamShared

sys.stdout.reconfigure(encoding='utf-8')

# ===== 路徑設定 =====
RAY_DIR = 'C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\teams\\ray'
REPORTS_DIR = os.path.join(RAY_DIR, 'reports')
LOG_FILE = os.path.join(REPORTS_DIR, 'dca_analysis_log.json')
PATTERNS_FILE = os.path.join(REPORTS_DIR, 'dca_patterns.json')
os.makedirs(REPORTS_DIR, exist_ok=True)

# 預設 DCA ETF（Core 持股）
CORE_ETFS = ['0050', '0056', '00878', '00919']

# ===== 工具函式 =====

def load_analysis_log():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def get_etf_position(etf_id):
    """抓 ETF 在近1年區間的位置"""
    sym = etf_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1y')
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
        price = close.iloc[-1]
        low = close.min()
        high = close.max()
        return (price - low) / (high - low) * 100 if high > low else 50, float(price)
    except:
        return None, None


def weekly_review():
    """每週 DCA Review"""
    print()
    print('='*60)
    print(' Ray 每週 DCA Review')
    print(f' 時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*60)

    alerts = []
    for etf_id in CORE_ETFS:
        pos, price = get_etf_position(etf_id)
        if pos is None:
            continue

        if pos < 35:
            action = '🚀 強烈建議買進'
        elif pos < 50:
            action = '✅ 正常買進'
        elif pos < 65:
            action = '⚠️ 減少金額'
        else:
            action = '⏸️ 暫停申購'

        alerts.append({'etf_id': etf_id, 'position_pct': round(pos, 1), 'price': price, 'action': action})
        print(f'  {etf_id} | 位置: {pos:.1f}% | 價格: ${price:.2f} | {action}')

    print()
    try:
        twii = yf.Ticker('^TWII').history(period='1y')['Close']
        tp = (twii.iloc[-1] - twii.min()) / (twii.max() - twii.min()) * 100
        print(f'  TWII 總體位置: {tp:.1f}%')
    except:
        pass

    print('='*60)
    return alerts


def monthly_portfolio_review():
    """每月投資組合檢視"""
    print()
    print('='*60)
    print(' Ray 每月 Portfolio 檢視')
    print(f' 時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*60)

    log = load_analysis_log()
    etf_stats = {}
    for rec in log:
        etf = rec['etf']
        if etf not in etf_stats:
            etf_stats[etf] = {'positions': [], 'actions': []}
        etf_stats[etf]['positions'].append(rec.get('position_pct', 50))
        etf_stats[etf]['actions'].append(rec.get('action', ''))

    print()
    print('【Core ETF DCA 健康檢查】')
    for etf_id in CORE_ETFS:
        stats = etf_stats.get(etf_id, {})
        positions = stats.get('positions', [])
        if not positions:
            print(f'  {etf_id}: 尚無記錄')
            continue
        avg_pos = sum(positions) / len(positions)
        recent_pos = positions[-1]
        action_count = stats.get('actions', [])
        buy_count = sum(1 for a in action_count if '買' in str(a))
        health = '✅ 健康' if avg_pos < 55 else ('⚠️ 注意' if avg_pos < 70 else '❌ 偏高')
        print(f'  {etf_id}:')
        print(f'    平均位置: {avg_pos:.1f}% | 最新位置: {recent_pos:.1f}%')
        print(f'    歷史買進次數: {buy_count}/{len(action_count)}')
        print(f'    建議: {health}')

    print()
    print('【Pattern 學習】')
    analyze_patterns(log)

    print()
    print('【Ray 月度建議】')
    generate_monthly_recommendations(etf_stats)

    print('='*60)


def analyze_patterns(log):
    if len(log) < 10:
        print('  記錄不足，暫無 Pattern 分析')
        return
    low_entry = [r for r in log if r.get('position_pct', 100) < 40]
    high_entry = [r for r in log if r.get('position_pct', 0) >= 70]
    print(f'  低價進場 (< 40%): {len(low_entry)} 次')
    print(f'  高價進場 (>= 70%): {len(high_entry)} 次')
    patterns = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'low_entry_count': len(low_entry),
        'high_entry_count': len(high_entry),
        'total_records': len(log)
    }
    try:
        existing = json.load(open(PATTERNS_FILE, 'r', encoding='utf-8'))
    except:
        existing = []
    existing.append(patterns)
    existing = existing[-12:]
    with open(PATTERNS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f'  Pattern 已記錄 (共 {len(existing)} 筆記錄)')


def generate_monthly_recommendations(etf_stats):
    for etf_id in CORE_ETFS:
        stats = etf_stats.get(etf_id, {})
        positions = stats.get('positions', [])
        if not positions:
            continue
        avg_pos = sum(positions) / len(positions)
        if avg_pos < 40:
            rec = '維持或增加 DCA 金額，低價佈局'
        elif avg_pos < 60:
            rec = '維持正常 DCA 金額'
        elif avg_pos < 75:
            rec = '考慮減少 DCA 金額 30-50%'
        else:
            rec = '暫停 DCA，等待價格回落'
        print(f'  {etf_id}: {rec}')


def alert_low_price():
    """低價警報檢查"""
    print()
    print('=== Ray 低價警報檢查 ===')
    print()
    alerts_found = []
    for etf_id in CORE_ETFS:
        pos, price = get_etf_position(etf_id)
        if pos is None:
            continue
        if pos < 35:
            alerts_found.append({'etf_id': etf_id, 'position_pct': round(pos, 1), 'price': price})
            print(f'  🚨 {etf_id}: 價格位置 {pos:.1f}%（低於35%），DCA 極佳時機')
    if not alerts_found:
        print('  目前無低價警報')
    try:
        shared = TeamShared()
        for a in alerts_found:
            shared.write_alert('DCA_LOW_PRICE', f"Ray: {a['etf_id']} 價格位置 {a['position_pct']}%（低價 DCA 機會）", 'info')
    except:
        pass
    return alerts_found


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'weekly'
    if mode == 'weekly':
        weekly_review()
    elif mode == 'monthly':
        monthly_portfolio_review()
    elif mode == 'alert':
        alert_low_price()
    else:
        print(f'未知模式: {mode}')
        print('用法: python dca_scheduler.py [weekly|monthly|alert]')
