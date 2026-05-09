# -*- coding: utf-8 -*-
"""
Sentiment Analyzer — 新聞情緒分析核心 v2
繁體中文優先，支援中英日韓關鍵字
"""
import re
import sys

# ========== 正面關鍵字 ==========
POSITIVE_KEYWORDS = [
    # 繁體中文
    '漲', '突破', '新高', '利多', '成長', '優於', '買進', '佳', '看好', '爆發',
    '大漲', '強勁', '超標', '驚艷', '史上新高', '超預期', '優異', '成長動能',
    '狂飆', '飆漲', '亮眼', '攀升', '反彈', '回升', '復甦', '創高', '勁揚',
    '暢旺', '訂單湧入', '缺口向上的', '多頭格局', '法人青睞', '買超',
    '漲停', '攻上', '挑戰', '超越', '達標', '擴產', '增產', '擴廠',
    # 簡體（自動轉換）
    '大涨', '突破', '利多', '成长', '优于', '买进', '看好', '爆发',
    # 英文
    'beat', 'beats', 'bullish', 'upgrade', 'gain', 'rally', 'soar', 'jump',
    'outperform', 'strong', 'surge', 'optimistic', 'upside', 'high', 'rally',
    'growth', 'profit', 'profitable', 'buy', 'rising', 'climb', 'jump',
    # 日文
    '上昇', '新高値', '買増', '好決算',
]

# ========== 負面關鍵字 ==========
NEGATIVE_KEYWORDS = [
    # 繁體中文
    '跌', '跌破', '新低', '利空', '衰退', '不如', '賣出', '虧', '看淡', '崩',
    '大跌', '疲弱', '未達', '憂慮', '下滑', '危機', '暴跌', '虧損', '失望',
    '警示', '跌破', '崩跌', '殺低', '狂瀉', '破底', '破線', '慘跌',
    '警訊', '隱憂', '逆風', '降評', '調降', '砍單', '庫存過高', '虧錢',
    '套牢', '追蹤', '警示', '注意', '警戒', '過熱', '風險',
    # 簡體
    '大跌', '跌破', '利空', '衰退', '卖出', '亏损', '看淡', '崩',
    # 英文
    'miss', 'bearish', 'downgrade', 'fall', 'drop', 'plunge', 'cut', 'weak',
    'decline', 'concern', 'warning', 'loss', 'lose', 'falling', 'sink',
    'sell', 'below', 'low', 'risk', 'fear', 'cut', 'reduce', 'halt',
    # 日文
    '下落', '最安値', '売増', '減益',
]

# ========== 強度關鍵字（加強情緒） ==========
STRONG_POSITIVE = [
    '大漲', '爆發', '史上新高', '超預期', '驚艷', 'beats', 'surge', 'soar',
    '狂飆', '飆漲', '亮眼', '缺口向上', '多頭格局', '漲停',
]
STRONG_NEGATIVE = [
    '大跌', '暴跌', '危機', '崩盤', 'plunge', 'crash', 'warning',
    '狂瀉', '崩跌', '破底', '套牢', '砍單', '庫存過高',
]

# ========== 行業分類 ==========
CATEGORY_KEYWORDS = {
    'semiconductor': [
        '半導體', '晶片', '積體電路', 'IC', '台積電', '輝達', 'nvidia', '台積',
        '半導體設備', '封測', '先進製程', '成熟製程', 'EUV', 'CoWoS',
        '聯發科', '聯電', '日月光', '力成', '欣興', '景碩',
        '半導體', '芯片', 'IC設計', '晶圓代工',
    ],
    'ai': [
        'AI', '人工智慧', '機器學習', 'deep learning', 'chatgpt', '人工智慧',
        '生成式AI', '大型語言模型', 'LLM', 'AI伺服器', 'AI概念股',
        'Copilot', 'Gemini', 'Claude', '馬斯克', 'Neuralink',
    ],
    'banking': [
        '銀行', '金控', '壽險', '中信', '富邦', '國泰', '兆豐', '華南',
        '王道銀行', '玉山', '永豐', '第一金', '合庫',
    ],
    'energy': [
        '能源', '石油', '天然氣', '風電', '太陽能', '油價', '電價',
        '離岸風電', '光電', '綠能', '氫能', '燃油',
    ],
    'retail': [
        '零售', '消費', '餐飲', '電商', 'momo', '東森', '富邦媒',
        '網家', '商店街', '線上購物', '餐飲', '超商', '超市',
    ],
    'macro': [
        '央行', 'CPI', 'GDP', '利率', '通膨', '景氣', '經濟數據', 'Fed', '聯準會',
        '升息', '降息', '縮表', 'QE', '量化寬鬆', '美國聯準會', 'FOMC',
        '消費者物價', '生產者物價', '進出口', '貿易戰', '關稅',
    ],
    'earnings': [
        '財報', '營收', 'EPS', '季報', '年報', '獲利', '盈利',
        '營益率', '毛利率', '每股盈餘', '財測', '法說會', '業績',
    ],
    'auto': [
        '車用', '電動車', 'Tesla', '比亞迪', '和泰', '裕隆', '鴻海',
        '特斯拉', 'MIH', '電車', '自驾', '輔助駕駛',
    ],
    'tech': [
        '科技', '蘋果', 'Google', 'Meta', 'Amazon', 'Microsoft', 'Netflix',
        'iPhone', 'Android', 'APPLE', '軟體', '硬體', '網路',
    ],
    'shipbuilding': [
        '造船', '貨櫃', '海運', '航運', '陽明', '長榮', '萬海',
        '運價', 'Container', '航線', '塞港', '缺船', '缺櫃',
    ],
    'medical': [
        '生技', '製藥', '醫材', '疫苗', '新藥', '臨床', 'FDA',
        '高端', '聯亞', '國光', '浩鼎', '學名藥', '生技股',
    ],
}

def normalize_text(text):
    """簡繁轉換 + 統一小寫"""
    # 簡體→繁體（常見詞）
    simplified_map = {
        '大涨': '大漲', '突破': '突破', '利多': '利多', '成长': '成長',
        '优于': '優於', '买进': '買進', '看好': '看好', '爆发': '爆發',
        '大跌': '大跌', '跌破': '跌破', '利空': '利空', '衰退': '衰退',
        '卖出': '賣出', '亏损': '虧損', '看淡': '看淡', '崩': '崩',
    }
    result = text
    for sim, trad in simplified_map.items():
        result = result.replace(sim, trad)
    return result.lower()

def calc_sentiment(headline, content=''):
    """
    計算新聞情緒分數
    Returns: (sentiment: float -1.0~1.0, score_level: int 1-5)
    """
    if not headline or len(headline.strip()) < 3:
        return 0.0, 1
    
    # 標準化文字
    full_text = normalize_text(headline + ' ' + (content or ''))
    original_lower = (headline + ' ' + (content or '')).lower()
    
    pos_count = 0
    neg_count = 0
    
    for kw in POSITIVE_KEYWORDS:
        if kw.lower() in original_lower:
            pos_count += 1
    
    for kw in NEGATIVE_KEYWORDS:
        if kw.lower() in original_lower:
            neg_count += 1
    
    # 基礎情緒
    if pos_count > neg_count:
        sentiment = min(1.0, 0.25 + (pos_count - neg_count) * 0.12)
    elif neg_count > pos_count:
        sentiment = max(-1.0, -0.25 - (neg_count - pos_count) * 0.12)
    else:
        sentiment = 0.0
    
    # 強度調整
    for k in STRONG_POSITIVE:
        if k.lower() in original_lower:
            sentiment = min(1.0, sentiment + 0.2)
            break
    
    for k in STRONG_NEGATIVE:
        if k.lower() in original_lower:
            sentiment = max(-1.0, sentiment - 0.2)
            break
    
    # 複雜度評分
    abs_sent = abs(sentiment)
    if abs_sent < 0.15:
        score_level = 1
    elif abs_sent < 0.35:
        score_level = 2
    elif abs_sent < 0.65:
        score_level = 3
    elif abs_sent < 0.85:
        score_level = 4
    else:
        score_level = 5
    
    return round(sentiment, 3), score_level

def detect_category(headline, content=''):
    """自動偵測新聞類別"""
    text = (headline + ' ' + (content or '')).lower()
    matches = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            if cat not in matches:
                matches.append(cat)
    return matches if matches else ['general']

def get_sentiment_label(sentiment):
    """取得情緒標籤"""
    if sentiment >= 0.5:
        return '極度看好'
    elif sentiment >= 0.2:
        return '正向'
    elif sentiment >= 0.05:
        return '略佳'
    elif sentiment >= -0.05:
        return '中立'
    elif sentiment >= -0.2:
        return '略差'
    elif sentiment >= -0.5:
        return '負向'
    else:
        return '極度看淡'

if __name__ == '__main__':
    # 測試
    tests = [
        '輝達財報驚艷 AI需求大爆發 股價大漲10%',
        '央行宣布升息 經濟放緩憂慮加劇',
        '台積電法說會：先進製程需求強勁 訂單塞滿',
        '科技股殺盤 美股暴跌300點 投資人慌拋售',
        '聯發科新晶片亮相 效能超車高通 明年拚擴產',
        '航運價格回檔 陽明長榮面臨壓力 法人降評',
        'Fed升息3碼 鮑爾：對抗通膨決心不變',
        'Apple財報優於預期 iPhone需求旺 宣布回購股票',
    ]
    print("Sentiment Analysis Test (v2)")
    print("=" * 70)
    for t in tests:
        sent, lvl = calc_sentiment(t)
        cats = detect_category(t)
        label = get_sentiment_label(sent)
        bar = '+' * int(max(0, sent * 10)) if sent > 0 else '-' * int(max(0, abs(sent) * 10))
        print(f"[{sent:+.3f} L{lvl} {label:4s}] {bar}")
        print(f"  {t[:50]}...")
        print(f"  => {cats}")