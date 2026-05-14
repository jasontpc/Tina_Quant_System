"""
Tina 模擬倉日檢討腳本
stores/portfolio/daily_review.py

用法:
  python daily_review.py --mode trade   # 收盤檢討（持倉調整）
  python daily_review.py --mode scan    # 开盘前掃描（新倉機會）
  python daily_review.py --mode status   # 快速狀態查詢
"""

import json
import sys
import os
from datetime import datetime, date

def load_positions():
    path = os.path.join(os.path.dirname(__file__), 'positions.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_positions(data):
    path = os.path.join(os.path.dirname(__file__), 'positions.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_trade(action, symbol, qty, price, reason):
    log_path = os.path.join(os.path.dirname(__file__), 'trades.log')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    line = f"[{ts}] {symbol} | ACTION: {action} | QTY: {qty} | PRICE: {price} | REASON: {reason}\n"
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(line)

def health_score(pos):
    """計算持倉健康分 0-100"""
    score = 100
    rsi = pos['last_check']['rsi']
    pnl = pos['last_check']['pnl_pct']
    macd_hist = pos['last_check']['macd_hist']
    price = pos['last_check']['price']
    ma20 = pos['last_check']['ma20']

    if rsi > 75: score -= 40
    elif rsi > 70: score -= 25
    elif rsi > 65: score -= 10

    if pnl > 10: score -= 20
    elif pnl > 8: score -= 10
    if pnl < 0: score -= max(15, abs(pnl) * 2)

    if macd_hist < 0: score -= 25
    if price < ma20: score -= 20

    return max(0, score)

def get_health_label(score):
    if score >= 75: return '🟢 健康'
    if score >= 50: return '🟡 觀察'
    return '🔴 出局'

def check_exit_conditions(pos, twii_rsi=None):
    """檢查是否觸發出场條件"""
    checks = []
    rsi = pos['last_check']['rsi']
    pnl = pos['last_check']['pnl_pct']
    price = pos['last_check']['price']
    ma20 = pos['last_check']['ma20']
    macd_hist = pos['last_check']['macd_hist']

    if pnl <= -8:
        checks.append(('STOP_LOSS', '虧損-8%止損'))
    elif pnl <= -5:
        checks.append(('WARN_LOSS', '虧損-5%預警'))
    if pnl >= 8:
        checks.append(('TAKE_PROFIT', '盈利+8%目標'))
    if rsi > 75:
        checks.append(('RSI_OVERHEATED', f'RSI {rsi:.0f}>75過熱'))
    if rsi > 70 and pnl > 5:
        checks.append(('CONSIDER_HALF', 'RSI>70+盈利可收割'))
    if price < ma20:
        checks.append(('BELOW_MA20', '跌破MA20'))
    if macd_hist < 0:
        checks.append(('MACD_DEATH_CROSS', 'MACD死叉'))
    if twii_rsi and twii_rsi > 85:
        checks.append(('TWII_OVERHEATED', f'TWII RSI {twii_rsi:.0f}>85系統減碼'))

    # 最高優先級
    for action, reason in checks:
        if action in ('STOP_LOSS', 'TWII_OVERHEATED') and pnl < 0:
            return action, reason

    if checks:
        return checks[0][0], checks[0][1]
    return 'HOLD', '正常持有'

def review_positions(twii_rsi=None):
    """收盤檢討模式"""
    data = load_positions()
    recommendations = []

    for pos in data['positions']:
        score = health_score(pos)
        health = get_health_label(score)
        action, reason = check_exit_conditions(pos, twii_rsi)

        print(f"\n{'='*50}")
        print(f"[{pos['symbol']}] {pos['name']}")
        print(f"  現價: {pos['last_check']['price']:.1f} | 成本: {pos['cost']:.1f}")
        print(f"  損益: {pos['last_check']['pnl_pct']:+.1f}%")
        print(f"  RSI: {pos['last_check']['rsi']:.1f} | MACD Hist: {pos['last_check']['macd_hist']:+.2f}")
        print(f"  健康分: {score} {health}")
        print(f"  建議: {action} — {reason}")

        pos['health_score'] = score
        pos['health_label'] = health
        pos['action'] = action
        pos['action_reason'] = reason
        recommendations.append({
            'symbol': pos['symbol'],
            'name': pos['name'],
            'action': action,
            'reason': reason,
            'score': score
        })

    save_positions(data)
    return recommendations

def scan_new_entries():
    """開盤前掃描模式 — 新倉機會（目前不执行，預留介面）"""
    print("新倉掃描模式 — 預留功能")
    print("觸發條件：RSI < 65, MACD Hist > 0, TWII RSI < 80")
    return []

def show_status():
    """快速狀態查詢"""
    data = load_positions()
    total_value = 0
    total_pnl = 0

    print(f"\n{'='*60}")
    print(f"  模擬倉狀態 — {date.today()}")
    print(f"{'='*60}")
    print(f"{'Symbol':<12} {'現價':>8} {'成本':>8} {'損益':>8} {'RSI':>6} {'狀態':>10}")
    print(f"{'-'*60}")

    for pos in data['positions']:
        lc = pos['last_check']
        pnl = lc['pnl_pct']
        total_value += lc['price'] * pos['shares']
        total_pnl += (lc['price'] - pos['cost']) * pos['shares']

        print(f"{pos['symbol']:<12} {lc['price']:>8.1f} {pos['cost']:>8.1f} {pnl:>+7.1f}% {lc['rsi']:>5.1f} {pos['action'] or 'HOLD':>10}")

    print(f"{'-'*60}")
    print(f"總市值: {total_value/10000:.1f}萬 | 總損益: {total_pnl/10000:+.1f}萬")
    print(f"，持倉%: {total_value/data['portfolio_value']*100:.1f}%")

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if mode == '--mode':
        mode = sys.argv[2] if len(sys.argv) > 2 else 'status'

    if mode == 'trade':
        twii_rsi = float(sys.argv[2]) if len(sys.argv) > 2 else None
        recs = review_positions(twii_rsi)
        print(f"\n\n共 {len(recs)} 檔持倉檢討完成")
    elif mode == 'scan':
        scan_new_entries()
    elif mode == 'status':
        show_status()
    else:
        print(f"用法: python daily_review.py [trade|scan|status]")