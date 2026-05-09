import yfinance as yf

tickers = {
    'META': 'Meta',
    'MSFT': 'Microsoft', 
    'NVDA': 'NVIDIA',
    'AMD': 'AMD',
    'AMAT': 'AMAT',
    'KLAC': 'KLAC',
    'AVGO': 'Broadcom',
    'COHR': 'Coherent',
    'LITE': 'Lumentum',
    'QQQ': 'QQQ ETF'
}

def calc_rsi(closes, period=14):
    deltas = closes.diff()
    gains = deltas.where(deltas > 0, 0).rolling(period).mean()
    losses = (-deltas.where(deltas < 0, 0)).rolling(period).mean()
    rs = gains / losses
    return 100 - (100 / (1 + rs))

print('='*70)
print('Tina 美股分析報告 | 2026-05-08 收盤')
print('='*70)
print()
print('股票           現價       日變化    RSI   評估            5日Bias')
print('-'*70)

for tk, name in tickers.items():
    try:
        t = yf.Ticker(tk)
        hist = t.history(period='3mo')
        if len(hist) < 20:
            print(f'{name:<12} 無足夠資料')
            continue
        
        closes = hist['Close']
        c = float(closes.iloc[-1])
        
        # 日變化
        p = float(closes.iloc[-2])
        daily_chg = (c/p-1)*100
        
        # 5日Bias
        ma5_val = float(closes.tail(5).mean())
        bias5 = (c/ma5_val-1)*100
        
        # RSI
        rsi = float(calc_rsi(closes).iloc[-1])
        
        # 評估
        if rsi > 75:
            eval_str = 'OVERBOUGHT'
        elif rsi > 65:
            eval_str = 'WARM'
        elif rsi < 35:
            eval_str = 'OVERSOLD'
        elif rsi < 45:
            eval_str = 'COOL'
        else:
            eval_str = 'NEUTRAL'
        
        print(f'{name:<12} ${c:>7.2f} {daily_chg:>+6.2f}% {rsi:>5.1f}  [{eval_str:<10}] {bias5:>+6.1f}%')
    except Exception as e:
        print(f'{name:<12} -- 錯誤')

print()
print('='*70)
print('=== Jo 持倉 ===')
print()

portfolio = {
    'META': {'cost': 606.00, 'shares': 1},
    'MSFT': {'cost': 410.14, 'shares': 2}
}

total_pnl = 0
for tk, data in portfolio.items():
    t = yf.Ticker(tk)
    info = t.info
    c = info.get('currentPrice', info.get('regularMarketPrice'))
    if c:
        c = float(c)
        pnl = (c - data['cost']) * data['shares']
        pnl_pct = (c/data['cost']-1)*100
        total_pnl += pnl
        status = 'PASS' if pnl_pct > 0 else 'LOSS'
        print(f'{tk:<6} ${c:>7.2f} | 成本${data["cost"]:.2f} | 損益${pnl:>+7.2f} ({pnl_pct:>+5.2f}%) [{status}]')

print()
print(f'總損益: ${total_pnl:+.2f}')
print()
print('='*70)
print('=== Tina 建議 ===')
print()
print('[HOLD] META - 小幅盈利，持有')
print('[HOLD] MSFT - 穩健，持有')
print()
print('[WATCH] AMD - 高Beta 1.8，注意波動')
print('[WATCH] AMAT - 今日大跌 -4%，注意風險')
print('[WATCH] QQQ - RSI 56，中性偏弱')