import re

with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\decision_committee_vote.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Comprehensive Chinese to ASCII replacement map
replacements = {
    '表決模組': 'Vote Module',
    '使用方式': 'Usage',
    '委員': 'Member',
    '門檻': 'Threshold',
    '提案': 'Proposal',
    '票數不足': 'Insufficient votes',
    '自動改為': 'Auto-change to',
    '決策委員會表決': 'Committee Vote',
    '買進': 'Buy',
    '賣出': 'Sell',
    '持有': 'Hold',
    '觀察': 'Watch',
    '跳過': 'Skip',
    '時間': 'Time',
    '現價': 'Price',
    '各委員投票': 'Member Votes',
    '票數統計': 'Vote Tally',
    '贊成': 'Agree',
    '反對': 'Disagree',
    '棄權': 'Abstain',
    '觀望': 'Watch',
    '門檻：委員同意': 'Threshold: /5 agree',
    '結果': 'Result',
    '執行': 'Execute',
    '否決': 'Veto',
    '建議觀望': 'Recommend Watch',
    '暫不執行': 'Do not execute',
    '委員會未能達成共識': 'No Consensus',
    '信心加權': 'Confidence',
    '（門檻）': '(threshold)',
    '委員分布': 'Vote distribution',
    '少數優勢': 'Minority majority',
    '支持買入': 'Support buy',
    '信心度': 'Conf',
    '理由': 'Reason',
    '標籤': 'Tags',
    '無': 'none',
    '勝率': 'Win Rate',
    '綜合評分不足': 'Score too low',
    'MA多頭排列': 'MA Bull Align',
    '區間OK': 'Range OK',
    'ATR停損': 'ATR Stop',
    '縮小部位': 'Reduce size',
    '合理': 'OK',
    '歷史報酬': 'Hist Return',
    '基本面佳但技術面偏弱': 'Fundamental OK, tech weak',
    'Macro中性偏觀望': 'Macro Neutral-Watch',
    '總經不確定性': 'Macro uncertainty',
    '勝率不足進場': 'Win rate insufficient',
    '波段交易員觀點': 'Swing Trader View',
    '波段規則': 'Swing Rules',
    '超賣可能反彈': 'Oversold, bounce possible',
    '過高': 'Too high',
    '低波動率': 'Low volatility',
    '區間': 'Range',
    '波動縮小部位': 'Vol reduce position',
    '歷史': 'Hist',
    '分析師觀點': 'Analyst View',
    'EPS': 'EPS',
    '營收成長': 'Rev growth',
    '毛利率': 'Gross margin',
    '無足夠數據': 'No enough data',
    '在黑名單': 'On blacklist',
    'ETF資產配置觀點': 'ETF Allocator View',
    'DCA理想進場': 'DCA ideal entry',
    '月均線多頭': 'MA bullish',
    '歷史平均': 'Hist avg',
    '總經策略師觀點': 'Macro Strategist View',
    'GDP預測': 'GDP forecast',
    '高通膨': 'High inflation',
    '利率走向': 'Rate direction',
    '地緣風險': 'Geopolitical risk',
    'AI伺服器需求旺': 'AI server demand strong',
    '半導體分析師觀點': 'Semiconductor analyst view',
    'TSMC法說': 'TSMC call',
    'TSMC法說優於預期': 'TSMC call beat',
    '獲利率顯著提升': 'Margin improve',
    '最終決策觀點': 'Final Decision View',
}

for cn, en in replacements.items():
    content = content.replace(cn, en)

# Also replace fullwidth brackets
content = content.replace('（', '(').replace('）', ')')
content = content.replace('【', '[').replace('】', ']')
content = content.replace('─', '-').replace('━', '-')
content = content.replace('→', '->')
content = content.replace('•', '-')

# Remove any remaining non-ASCII characters
# Keep basic punctuation
content = content.encode('ascii', 'replace').decode('ascii')

# Clean up replacement artifacts
content = content.replace('? ', '').replace(' ?', '')
content = re.sub(r'\s+', ' ', content)

with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\decision_committee_vote.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("All Chinese replaced, file saved")
print(f"File length: {len(content)} chars")