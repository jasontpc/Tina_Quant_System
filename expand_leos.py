d = open('teams/leadtrades/leos/leos_v65.py', encoding='utf-8').read()

old_monitor = "MONITOR_STOCKS = {\n    '2330': '台積電', '2454': '聯發科', '2317': '鴻海',\n    '2379': '瑞昱', '2376': '技嘉', '2382': '廣達',\n    '3665': '穎崴', '3034': '緯穎',\n}"

new_monitor = """# === 擴充科技股池（半導體/AI/光通訊/CPO/記憶體/儲存）===
MONITOR_STOCKS = {
    # 半導體
    '2330': '台積電', '2454': '聯發科', '2303': '聯電',
    # AI伺服器/組裝
    '2317': '鴻海', '2382': '廣達', '3034': '緯穎',
    # AI板卡/高速運算
    '2376': '技嘉', '2379': '瑞昱',
    # 先進封裝/測試
    '3665': '穎崴',
    # 散熱
    '2456': '奇鋐', '3533': '嘉澤',
    # 光通訊/CPO
    '3532': '昇達科', '2371': '華星光',
    # 高速傳輸/連接
    '3443': '創惟',
    # 半導體通路/代理
    '6717': '大聯大',
}

# === 美股科技股池 ===
US_STOCKS = {
    # AI GPU/IC設計
    'NVDA': 'NVIDIA', 'AMD': 'AMD', 'QCOM': 'Qualcomm', 'ARM': 'ARM',
    # 記憶體
    'MU': 'Micron', 'WDC': 'Western Digital', 'STX': 'Seagate',
    # 光通訊/CPO
    'ANET': 'Arista', 'LITE': 'Lumentum', 'COHR': 'Coherent',
    # 雲端/AI基礎設施
    'AMZN': 'Amazon', 'MSFT': 'Microsoft', 'GOOGL': 'Google', 'META': 'Meta',
    # 半導體設備
    'AMAT': 'Applied Mat', 'LRCX': 'Lam Research', 'KLAC': 'KLA', 'SNPS': 'Synopsys', 'ASML': 'ASML',
    # 高速網路
    'MRVL': 'Marvell', 'AVGO': 'Broadcom',
}"""

if old_monitor in d:
    d = d.replace(old_monitor, new_monitor, 1)
    print('MONITOR_STOCKS expanded!')
else:
    print('Pattern not found - checking...')
    # Show what's there
    idx = d.find("MONITOR_STOCKS = {")
    if idx >= 0:
        print(repr(d[idx:idx+300]))

open('teams/leadtrades/leos/leos_v65.py', 'w', encoding='utf-8').write(d)