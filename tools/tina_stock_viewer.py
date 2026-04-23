# -*- coding: utf-8 -*-
"""
Tina 即時股價查詢工具
輸入股票代號，即時顯示價格與技術指標
"""
import sys
import threading
import tkinter as tk
from tkinter import ttk
import yfinance as yf
import numpy as np

# 全域變數
current_data = {}

def fetch_stock():
    code = entry.get().strip().upper()
    if not code:
        return
    
    # 處理代碼
    if not code.endswith('.TW'):
        code = code + '.TW'
    
    result_text.set("載入中...")
    root.update()
    
    try:
        # 抓取資料
        t = yf.Ticker(code)
        h = t.history(period='10d')
        
        if h is None or len(h) < 2:
            result_text.set(f"找不到股票 {entry.get()}")
            return
        
        # 計算
        prices = list(h['Close'])
        current = float(prices[-1])
        prev = float(prices[-2])
        change = (current / prev - 1) * 100
        
        ma5 = np.mean(prices[-5:]) if len(prices) >= 5 else current
        ma10 = np.mean(prices[-10:]) if len(prices) >= 10 else current
        ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else current
        
        d = np.diff(prices)
        g = np.where(d > 0, d, 0)
        l = np.where(d > 0, 0, -d)
        ag = np.mean(g[-14:])
        al = np.mean(l[-14:])
        rs = 100 - (100 / (1 + ag / al)) if al != 0 else 50
        
        trs = []
        for i in range(-5, 0):
            hi = float(h['High'].iloc[i])
            lo = float(h['Low'].iloc[i])
            cl_p = float(h['Close'].iloc[i-1]) if i-1 >= 0 else current
            trs.append(max(hi-lo, abs(hi-cl_p), abs(lo-cl_p)))
        atr = np.mean(trs) if trs else 0
        atr_pct = atr / current * 100
        
        bias = (current / ma20 - 1) * 100
        
        vol = list(h['Volume'])
        vr = vol[-1] / np.mean(vol[-5:]) if np.mean(vol[-5:]) > 0 else 0
        
        # RSI 顏色
        if rs >= 85:
            rs_color = "🔴"
        elif rs >= 70:
            rs_color = "🟠"
        elif rs >= 50:
            rs_color = "🟡"
        else:
            rs_color = "🟢"
        
        # 漲跌符號
        arrow = "▲" if change > 0 else "▼" if change < 0 else "―"
        change_color = "green" if change > 0 else "red" if change < 0 else "gray"
        
        info = f"""📈 {entry.get()}

【價格】
 {arrow} {current:.2f} ({change:+.2f}%)

【均線】
 MA5:  {ma5:.2f}  {'↑' if current > ma5 else '↓'}
 MA10: {ma10:.2f} {'↑' if current > ma10 else '↓'}
 MA20: {ma20:.2f} {'↑' if current > ma20 else '↓'}

【技術】
 RSI: {rs_color} {rs:.1f}
 ATR: {atr_pct:.2f}%
 Bias: {bias:+.2f}%
 VR: {vr:.2f}

 更新: {h.index[-1].strftime('%Y-%m-%d %H:%M')}"""
        
        result_text.set(info)
        
    except Exception as e:
        result_text.set(f"錯誤: {str(e)}")

def on_enter(event):
    fetch_stock()

# 建立視窗
root = tk.Tk()
root.title("Tina 即時股價查詢")
root.geometry("400x450")
root.resizable(False, False)

# 標題
title = tk.Label(root, text="Tina 即時股價查詢", font=("Arial", 18, "bold"), fg="#2E86AB")
title.pack(pady=10)

# 說明
desc = tk.Label(root, text="輸入台股代號 (如: 2330, 0050)", font=("Arial", 10), fg="gray")
desc.pack()

# 輸入框
frame = tk.Frame(root)
frame.pack(pady=10)

entry = tk.Entry(frame, font=("Arial", 16), width=12, justify="center")
entry.pack(side=tk.LEFT, padx=5)
entry.focus()

btn = tk.Button(frame, text="查詢", font=("Arial", 14), command=fetch_stock, bg="#2E86AB", fg="white")
btn.pack(side=tk.LEFT)

# 綁定 Enter 鍵
entry.bind('<Return>', on_enter)

# 快捷按鈕
quick_frame = tk.Frame(root)
quick_frame.pack(pady=5)

tk.Label(root, text="快捷:", font=("Arial", 9), fg="gray").pack()

quick_codes = [("2330", "台積電"), ("2317", "鴻海"), ("0050", "0050"), ("2454", "聯發科")]
for code, name in quick_codes:
    b = tk.Button(quick_frame, text=code, font=("Arial", 9), command=lambda c=code: (entry.delete(0, tk.END), entry.insert(0, c), fetch_stock()))
    b.pack(side=tk.LEFT, padx=2)

# 結果顯示
result_frame = tk.Frame(root, bg="#f0f0f0", relief="sunken", bd=1)
result_frame.pack(fill="both", expand=True, padx=10, pady=10)

result_text = tk.StringVar()
result_label = tk.Label(result_frame, textvariable=result_text, font=("Consolas", 11), justify="left", anchor="nw")
result_label.pack(fill="both", expand=True, padx=10, pady=10)

# 底部版權
footer = tk.Label(root, text="Tina Quant System v3.12", font=("Arial", 8), fg="silver")
footer.pack(pady=5)

# 啟動
root.mainloop()