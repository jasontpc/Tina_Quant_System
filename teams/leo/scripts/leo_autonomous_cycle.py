import sys, json, os, yfinance as yf
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

TRADES_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\leo_trades.json'
ANALYSIS_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\leo_analysis.json'

ENTRY_RSI_MAX = 65
EXIT_RSI_MIN = 70
# === 進出場參數（百分比）===
TAKE_PROFIT_PCT = 200.0     # 20% 目標價（實際使用）
STOP_LOSS_PCT = 200.0       # 8% 停損（實際使用）
MAX_POSITION = 100000
COOLDOWN_MINUTES = 30

MONITOR_STOCKS = {
    '2330': '台積電', '2454': '聯發科', '2317': '鴻海', '2379': '瑞昱',
    '2376': '技嘉', '2382': '廣達', '3665': '穎崴', '3034': '緯穎',
}

def analyze_all():
    results = []
    for symbol, name in MONITOR_STOCKS.items():
        ticker = f'{symbol}.TW'
        h = yf.Ticker(ticker).history(period='3mo')
        if len(h) < 20:
            continue
        closes = h['Close'].dropna()
        cur = closes.iloc[-1]
        ma20 = closes.rolling(20).mean().iloc[-1]
        ma60 = closes.rolling(60).mean().iloc[-1] if len(closes) >= 60 else None
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        vol5 = h['Volume'].rolling(5).mean().iloc[-1]
        vol_now = h['Volume'].iloc[-1]
        from_high = (cur - closes.max()) / closes.max() * 100
        pos_ma20 = (cur - ma20) / ma20 * 100
        results.append({
            'symbol': symbol, 'name': name, 'price': round(cur, 2),
            'ma20': round(ma20, 2), 'pos_ma20': round(pos_ma20, 1),
            'ma60': round(ma60, 2) if ma60 else None,
            'rsi': round(rsi, 1), 'from_high': round(from_high, 1),
            'vol_ratio': round((vol_now / vol5) * 100, 0),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
    with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results

def load_trades():
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'trades': [], 'summary': {}}

def save_trades(data):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_recent_trade(symbol, minutes=30):
    trades_data = load_trades()
    cutoff = datetime.now() - timedelta(minutes=minutes)
    for t in trades_data.get('trades', []):
        if t.get('symbol') == symbol:
            try:
                trade_time = datetime.fromisoformat(t.get('timestamp',''))
                if trade_time >= cutoff:
                    return t
            except:
                pass
    return None

def run_cycle():
    print('=== Leo 自主學習迴圈 ===')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()

    # Step 1: 分析
    print('[Step 1] 分析8檔AI科技股...')
    analysis = analyze_all()
    current_prices = {a['symbol']: a for a in analysis}
    print(f'完成: {len(analysis)} 檔')

    # Step 2: 更新交易
    print('[Step 2] 檢查交易機會...')
    trades_data = load_trades()
    exits, entries = 0, 0

    # 檢查出场
    for t in trades_data.get('trades', []):
        if t.get('status') != 'open':
            continue
        sym = t['symbol']
        if sym not in current_prices:
            continue
        cur = current_prices[sym]['price']
        entry = t['entry_price']
        target = t.get('target_price', entry * 1.2)
        stop = t.get('stop_loss', entry * 0.92)
        reason = None
        if cur >= target:
            reason = 'take_profit'
        elif cur <= stop:
            reason = 'stop_loss'
        elif t.get('entry_rsi', 0) > 75 and current_prices[sym]['rsi'] > 85:
            reason = 'overheat'
        if reason:
            t['status'] = 'closed'
            t['exit_price'] = cur
            t['exit_reason'] = reason
            t['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            t['pnl'] = round((cur - entry) * t['shares'], 0)
            t['pnl_pct'] = round((cur - entry) / entry * 100, 2)
            exits += 1
            print(f'  出场 {sym}: {reason} -> {cur} ({t["pnl_pct"]:+.1f}%)')

    # 評估進場
    for stock in analysis:
        sym = stock['symbol']
        rsi = stock['rsi']
        pos_ma20 = stock['pos_ma20']
        price = stock['price']
        if get_recent_trade(sym, COOLDOWN_MINUTES):
            continue
        if rsi >= 45 and rsi <= ENTRY_RSI_MAX and pos_ma20 < 15:
            shares = int(MAX_POSITION / price)
            trade = {
                'symbol': sym, 'name': stock['name'],
                'entry_price': price, 'shares': shares,
                'amount': shares * price,
                'entry_rsi': rsi, 'entry_pos_ma20': pos_ma20,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'target_price': round(price * 1.20, 2),
                'stop_loss': round(price * 0.92, 2),
                'status': 'open',
                'trade_id': f'LEO_{sym}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
            }
            trades_data['trades'].append(trade)
            entries += 1
            print(f'  進場 {sym} {stock["name"]}: ${price} (RSI={rsi})')

    save_trades(trades_data)

    # Step 3: 摘要
    closed = [t for t in trades_data['trades'] if t.get('status') == 'closed']
    open_pos = [t for t in trades_data['trades'] if t.get('status') == 'open']
    total_pnl = sum(t.get('pnl', 0) for t in closed)
    win = [t for t in closed if t.get('pnl', 0) > 0]
    wr = len(win) / len(closed) * 100 if closed else 0
    avg_pnl = total_pnl / len(closed) if closed else 0

    print()
    print(f'總交易: {len(trades_data["trades"])} | 開倉: {len(open_pos)} | 已平: {len(closed)}')
    print(f'勝率: {wr:.0f}% | 總損益: NT${total_pnl:,.0f} | 平均: NT${avg_pnl:,.0f}')
    print()
    print(f'[Step 3] {exits}檔出场，{entries}檔新進場')
    return trades_data

if __name__ == '__main__':
    run_cycle()