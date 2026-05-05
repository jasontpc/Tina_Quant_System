# -*- coding: utf-8 -*-
import yfinance as yf
import json
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace")
AUDIT_LOG = WORKSPACE / "logs" / "db_audit.log"

def log(msg):
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
        f.write("[" + ts + "] " + msg + "\n")

def verify_rsi(c, period=14):
    if len(c) < period + 1:
        return None, "insufficient"
    d = c.diff()
    g = d.where(d>0, 0).rolling(period).mean()
    l = (-d.where(d<0, 0)).rolling(period).mean()
    rs = g / l
    rsi = (100 - (100 / (1 + rs)))
    return float(rsi.iloc[-1]), "ok"

def verify_ma(c, period):
    if len(c) < period:
        return None, "insufficient"
    ma = c.rolling(period).mean()
    return float(ma.iloc[-1]), "ok"

def verify_bias(price, ma):
    if ma is None or ma == 0:
        return None, "invalid"
    return ((price / ma) - 1) * 100, "ok"

def audit_symbol(sym, name):
    try:
        t = yf.Ticker(sym)
        h = t.history(period='3mo')
        c = h['Close'].dropna()
        if len(c) < 15:
            return {"symbol": name, "status": "ERROR", "msg": "insufficient data"}
        curr = float(c.iloc[-1])
        prev = float(c.iloc[-2])
        pct = ((curr - prev) / prev) * 100
        rsi, _ = verify_rsi(c)
        ma20, _ = verify_ma(c, 20)
        ma60, _ = verify_ma(c, 60)
        bias20, _ = verify_bias(curr, ma20)
        bias60, _ = verify_bias(curr, ma60)
        issues = []
        if rsi is None or rsi != rsi:
            issues.append("RSI NaN")
        if rsi is not None and (rsi < 0 or rsi > 100):
            issues.append("RSI out of range: " + str(rsi))
        if bias20 is not None and abs(bias20) > 50:
            issues.append("BIAS20 extreme: " + str(round(bias20, 1)) + "%")
        # Note: BIAS20 30-50% is elevated for uptrending stocks like 聯發科, not an error
        if curr <= 0 or curr != curr:
            issues.append("price error")
        status = "ERROR" if issues else "OK"
        return {
            "symbol": name,
            "price": round(curr, 2),
            "chg": round(pct, 2),
            "rsi": round(rsi, 1) if rsi else None,
            "ma20": round(ma20, 2) if ma20 else None,
            "bias20": round(bias20, 2) if bias20 else None,
            "status": status,
            "issues": issues,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    except Exception as e:
        return {"symbol": name, "status": "ERROR", "msg": str(e)[:50]}

def main():
    print("=== 資料庫檢核覆核 ===")
    log("=== 資料庫檢核覆核 ===")
    
    tw_stocks = [
        ('2330.TW', '2330 台積電'), ('2382.TW', '2382 廣達'),
        ('2454.TW', '2454 聯發科'), ('2317.TW', '2317 鴻海'),
        ('3034.TW', '3034 緯穎'), ('3231.TW', '3231 緯創'),
        ('3665.TW', '3665 穎崴'),
    ]
    tw_etfs = [
        ('0050.TW', '0050'), ('0056.TW', '0056'), ('00713.TW', '00713'),
        ('00878.TW', '00878'), ('00919.TW', '00919'),
    ]
    us_stocks = [
        ('NVDA', 'NVDA'), ('AMD', 'AMD'), ('MSFT', 'MSFT'), ('AAPL', 'AAPL'),
        ('GOOGL', 'GOOGL'), ('META', 'META'), ('AMZN', 'AMZN'),
        ('TSLA', 'TSLA'), ('SPY', 'SPY'), ('QQQ', 'QQQ'),
    ]
    
    all_symbols = tw_stocks + tw_etfs + us_stocks
    results = []
    errors = []
    
    for sym, name in all_symbols:
        result = audit_symbol(sym, name)
        results.append(result)
        rsi_str = str(round(result.get('rsi', 0) or 0, 1))
        bias_str = str(round(result.get('bias20', 0) or 0, 2))
        line = result['symbol'] + ": RSI=" + rsi_str + ", BIAS20=" + bias_str + "% - " + result['status']
        print(line)
        if result["status"] != "OK":
            errors.append(result)
            issues_str = str(result.get('issues', result.get('msg', 'unknown')))
            log("ERROR: " + name + " - " + issues_str)
    
    ok_count = len([r for r in results if r["status"] == "OK"])
    print("")
    print("=== 審計結果 ===")
    print("OK: " + str(ok_count) + "/" + str(len(results)))
    print("ERRORS: " + str(len(errors)))
    
    if errors:
        print("")
        print("=== 異常項目 ===")
        for e in errors:
            print("  " + e['symbol'] + ": " + str(e.get('issues', e.get('msg', 'unknown'))))
    
    report_file = WORKSPACE / "logs" / ("db_audit_" + datetime.now().strftime('%Y%m%d_%H%M') + ".json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total": len(results),
        "ok": ok_count,
        "errors": len(errors),
        "results": results
    }
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print("")
    print("報告已存: " + report_file.name)

if __name__ == '__main__':
    main()
