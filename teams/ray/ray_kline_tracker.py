# -*- coding: utf-8 -*-
"""
Ray K線追蹤模組 — 針對 15 檔 ETF 追蹤 K線低點
功能：
  - 每 30 分鐘更新一次（由 Cron 呼叫）
  - 計算與 52週/26週/12週低點的偏離%
  - 輸出 DCA 倍數建議
  - 發送推播（當偏離滿足條件時）
用法：
  python teams/ray/ray_kline_tracker.py
  python teams/ray/ray_kline_tracker.py --json    # 輸出 JSON
  python teams/ray/ray_kline_tracker.py 00919   # 單一 ETF
"""
import yfinance as yf
import pandas as pd
import sys
import os
import json
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray')
WORKSPACE = r'C:\Users\USER\.openclaw\workspace'

# 15檔監控ETF
MONITOR_ETFS = [
    '0050', '0056', '00878', '00891', '00919',
    '00927', '00713', '00646', '00662', '00757',
    '00923', '00915', '00917', '00918', '00920'
]

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00891': '中信低碳', '00919': '群益台灣精選', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00923': '凱基優選高股息', '00915': '兆豐永續高息',
    '00917': '中信關鍵半導體', '00918': '中信上游半導體', '00920': '中信特選金融'
}

# ============================================================
# 載入 .env
# ============================================================
ENV_FILE = os.path.join(WORKSPACE, '.env')
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1616824689')


# ============================================================
# K線低點分析
# ============================================================
def analyze_kline_low_points(ticker, period='1y'):
    """
    分析 K線相對低點，計算 DCA 倍數
    返回: dict 含 current_price, lows, deviations, dca_multiplier, recommendation
    """
    try:
        sym = ticker + '.TW'
        h = yf.Ticker(sym).history(period=period)
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']

        valid_close = close.dropna()
        if len(valid_close) == 0:
            return {'ticker': ticker, 'error': '無有效價格'}
        current_price = float(valid_close.iloc[-1])

        # 52週低點（252個交易日）
        if len(close) >= 252:
            low_52w = float(close.tail(252).min())
        else:
            low_52w = float(close.min())

        # 26週低點（126個交易日）
        if len(close) >= 126:
            low_26w = float(close.tail(126).min())
        else:
            low_26w = float(close.min())

        # 12週低點（60個交易日）
        if len(close) >= 60:
            low_12w = float(close.tail(60).min())
        else:
            low_12w = float(close.min())

        # 偏離計算
        deviation_52w = round((current_price - low_52w) / low_52w * 100, 2) if low_52w > 0 else 0
        deviation_26w = round((current_price - low_26w) / low_26w * 100, 2) if low_26w > 0 else 0
        deviation_12w = round((current_price - low_12w) / low_12w * 100, 2) if low_12w > 0 else 0

        # DCA 倍數判定
        if deviation_52w < 5:
            dca_multiplier = 2.0
            recommendation = '積極DCA (2倍)'
            alert_level = '🔴'
        elif deviation_26w < 5:
            dca_multiplier = 1.5
            recommendation = '加強DCA (1.5倍)'
            alert_level = '🟡'
        elif deviation_12w < 5:
            dca_multiplier = 1.2
            recommendation = '正常DCA (1.2倍)'
            alert_level = '🟡'
        elif deviation_52w > 20:
            dca_multiplier = 0.5
            recommendation = '觀望 (-50%)'
            alert_level = '🟢'
        else:
            dca_multiplier = 1.0
            recommendation = '正常DCA (1倍)'
            alert_level = '🟢'

        return {
            'ticker': ticker,
            'name': ETF_NAMES.get(ticker, ticker),
            'current_price': round(current_price, 2),
            'low_52w': round(low_52w, 2),
            'low_26w': round(low_26w, 2),
            'low_12w': round(low_12w, 2),
            'deviation_52w': deviation_52w,
            'deviation_26w': deviation_26w,
            'deviation_12w': deviation_12w,
            'dca_multiplier': dca_multiplier,
            'recommendation': recommendation,
            'alert_level': alert_level,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}


def analyze_all_kline():
    """分析所有 15 檔 ETF 的 K線低點"""
    results = []
    for ticker in MONITOR_ETFS:
        r = analyze_kline_low_points(ticker)
        results.append(r)
    return results


# ============================================================
# Telegram 發送
# ============================================================
def send_telegram(text: str, parse_mode='Markdown') -> bool:
    """發送 Telegram 訊息"""
    import requests
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': parse_mode
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f'[Ray KLine] Telegram 異常: {e}')
        return False


# ============================================================
# 推播建構
# ============================================================
def build_kline_alert(results: list) -> str:
    """建構 K線低點推播訊息"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [
        f'📊 *Ray K線低點追蹤*',
        f'🕐 {now} | {len(results)} 檔 ETF',
        '━' * 20
    ]

    # 按 DCA 倍數排序（倍數高的在前）
    sorted_results = sorted(
        [r for r in results if 'error' not in r],
        key=lambda x: x['dca_multiplier'],
        reverse=True
    )

    if not sorted_results:
        lines.append('無可用數據')
    else:
        lines.append('')
        lines.append('【DCA 倍數建議】')
        lines.append('')
        lines.append(f'{"ETF":<8s} {"名稱":<10s} {"現價":>7s} {"52W低點":>8s} {"偏離52W":>8s} {"倍數":>5s}  {"建議"}')
        lines.append('  ' + '-' * 65)
        for r in sorted_results:
            lines.append(
                f'{r["alert_level"]} {r["ticker"]:<6s} {r["name"]:<10s} '
                f'${r["current_price"]:>6.2f} ${r["low_52w"]:>7.2f} '
                f'{r["deviation_52w"]:>+7.2f}% ×{r["dca_multiplier"]:>4.1f}  {r["recommendation"]}'
            )

    lines.append('')
    lines.append('━' * 20)
    lines.append('🤖 Ray KLine | Tina System')

    return '\n'.join(lines)


def log_kline_results(results: list, filepath=None):
    """寫入 JSON 記錄"""
    if filepath is None:
        filepath = BASE_DIR / 'reports' / 'kline_tracker.json'
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# ============================================================
# 輸出報告
# ============================================================
def print_report(results: list, output_json=False):
    """輸出分析報告"""
    if output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print()
    print('=' * 70)
    print('【Ray K線低點追蹤報告 — 15檔ETF DCA 倍數建議】')
    print('=' * 70)
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()

    # 按倍數排序
    sorted_results = sorted(
        [r for r in results if 'error' not in r],
        key=lambda x: x['dca_multiplier'],
        reverse=True
    )

    print(f'{"ETF":<8s} {"名稱":<10s} {"現價":>7s} {"52W低":>7s} {"26W低":>7s} {"12W低":>7s} {"偏離52W":>8s} {"DCA×"}  {"建議"}')
    print('  ' + '-' * 78)

    for r in sorted_results:
        print(
            f'  {r["ticker"]:<6s} {r["name"]:<10s} '
            f'${r["current_price"]:>6.2f} ${r["low_52w"]:>6.2f} ${r["low_26w"]:>6.2f} ${r["low_12w"]:>6.2f} '
            f'{r["deviation_52w"]:>+7.2f}% ×{r["dca_multiplier"]:>4.1f}  {r["recommendation"]}'
        )

    print()
    print('【DCA 倍數說明】')
    print('  ×2.0  極佳買點 — 接近52週低點')
    print('  ×1.5  良好買點 — 接近26週低點')
    print('  ×1.2  普通買點 — 接近12週低點')
    print('  ×1.0  正常DCA')
    print('  ×0.5  觀望 — 偏離52週高點')
    print()

    # 摘要
    active = [r for r in sorted_results if r['dca_multiplier'] >= 1.5]
    cautious = [r for r in sorted_results if r['dca_multiplier'] < 1.0]

    print('【摘要】')
    if active:
        names = ', '.join([f'{r["name"]}({r["ticker"]})' for r in active])
        print(f'  🔴 積極DCA（×1.5+）: {names}')
    if cautious:
        names = ', '.join([f'{r["name"]}({r["ticker"]})' for r in cautious])
        print(f'  🟢 觀望（×0.5）: {names}')

    return sorted_results


# ============================================================
# 主程式
# ============================================================
def main():
    output_json = '--json' in sys.argv
    single_ticker = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else None

    print(f'\n[Ray KLine] 開始 K線低點追蹤 — {datetime.now().strftime("%Y-%m-%d %H:%M")}')

    if single_ticker and single_ticker in MONITOR_ETFS:
        results = [analyze_kline_low_points(single_ticker)]
        print(f'[Ray KLine] 單一模式: {single_ticker}')
    else:
        results = analyze_all_kline()
        print(f'[Ray KLine] 全量模式: {len(results)} 檔')

    # 輸出
    print_report(results, output_json=output_json)

    # 儲存
    log_kline_results(results)
    print(f'[Ray KLine] 結果已儲存')

    # 發送推播（只針對 ×2.0 或 ×1.5 的標的）
    hot_etfs = [r for r in results if 'error' not in r and r['dca_multiplier'] >= 1.5]
    if hot_etfs:
        alert_msg = build_kline_alert(results)
        if send_telegram(alert_msg):
            print(f'[Ray KLine] ✅ 推播已發送 ({len(hot_etfs)} 檔積極DCA)')
        else:
            print(f'[Ray KLine] ❌ 推播發送失敗')
    else:
        print(f'[Ray KLine] 無需推播（無 ×1.5+ 標的）')

    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
