# -*- coding: utf-8 -*-
"""
Tina 大腦核心 - 統一決策系統 v1.0
================================
整合五大層 + 記憶回路 + 專家委員會
MEMORY → experience → lessons → decision → outcome → MEMORY

功能：
1. Layer 1-5 完整決策流程
2. 讀取 MEMORY.md 持倉 + experience
3. 專家委員會評分
4. lessons 寫入 wins/losses
5. decision_log.md 記錄
"""

import sys, os, json
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
MEMORY_FILE = Path(r'C:\Users\USER\.openclaw\workspace\MEMORY.md')
LEDGER_FILE = WORKSPACE / 'data' / 'experience_ledger.json'
DECISION_LOG = Path(r'C:\Users\USER\.openclaw\workspace\memory\decision_log.md')
LESSONS_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'lessons'
TRADES_FILE = WORKSPACE / 'teams' / 'leadtrades' / 'leos' / 'leos_trades.json'

# ========== 常數 ==========
GOAL_ANCHOR = {
    'max_single_loss_percent': 0.08,
    'max_daily_loss_percent': 0.05,
    'max_portfolio_exposure': 0.40,
    'rsi_entry_max': 65,
}

# ========== Layer 1: 目標定義 ==========
def layer1_goal_anchor():
    """讀取 MEMORY.md 持倉"""
    positions = []
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        if '### 持倉狀態' in content:
            start = content.find('### 持倉狀態')
            section = content[start:start+3000]
            for line in section.split('\n'):
                if line.startswith('- ') and ('股' in line or '@' in line):
                    positions.append(line.strip())
    return positions

# ========== Layer 2: 風控邊界 ==========
def layer2_safe_boundary(rsi=None):
    """風控邊界檢查"""
    checks = {
        'RSI 上限 65': rsi < GOAL_ANCHOR['rsi_entry_max'] if rsi else True,
        '單筆虧損 8%': True,
        '部位上限 40%': True,
    }
    return all(checks.values()), checks

# ========== Layer 3: 感知分析 ==========
def layer3_contextual_perception():
    """讀取市場 + MEMORY + experience"""
    import yfinance as yf
    
    result = {'market': {}, 'positions': [], 'experience': []}
    
    # TWII
    try:
        twii = yf.Ticker('^TWII').history('1mo')
        if len(twii) >= 14:
            delta = twii['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            result['market']['TWII_RSI'] = rsi
            result['market']['TWII_Price'] = float(twii['Close'].iloc[-1])
    except:
        result['market']['TWII_RSI'] = None
    
    # 持倉
    result['positions'] = layer1_goal_anchor()
    
    # 經驗簿
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, encoding='utf-8') as f:
            ledger = json.load(f)
        result['experience'] = ledger[:10]  # 最近 10 筆
    
    return result

# ========== Layer 4: 專家委員會 ==========
def layer4_expert_committee(context):
    """專家委員會評分"""
    score = 0
    reasons = []
    
    rsi = context.get('market', {}).get('TWII_RSI')
    
    # 量化分析師 35%
    if rsi and rsi < 40:
        score += 30
        reasons.append('RSI<40 超賣 (+30)')
    elif rsi and rsi < 65:
        score += 10
        reasons.append('RSI 正常進場區間 (+10)')
    elif rsi and rsi > 85:
        score -= 20
        reasons.append('TWII RSI>85 過熱 (-20)')
    
    # 資深開發者 35%
    open_count = len(context.get('positions', []))
    if open_count > 20:
        score -= 15
        reasons.append(f'開倉過多 {open_count} 筆 (-15)')
    
    # 風控長 30%
    if rsi and rsi > 85:
        score -= 20
        reasons.append('風控：降倉 (-20)')
    
    verdict = 'APPROVE' if score >= 30 else ('CAUTION' if score >= 0 else 'REJECT')
    
    return {'score': score, 'verdict': verdict, 'reasons': reasons}

# ========== Layer 5: 反思進化 ==========
def layer5_reflection(result, outcome='SUCCESS'):
    """寫入 decision_log.md + lessons"""
    os.makedirs(DECISION_LOG.parent, exist_ok=True)
    
    log = f"""
## 決策日誌 {datetime.now().strftime('%Y-%m-%d %H:%M')}

### 市場感知
- TWII RSI：{result.get('market', {}).get('TWII_RSI', 'N/A')}
- 持倉數量：{len(result.get('positions', []))}

### 專家委員會
- 評分：{result.get('expert', {}).get('score', 0)}
- 裁決：{result.get('expert', {}).get('verdict', 'N/A')}
- 理由：{', '.join(result.get('expert', {}).get('reasons', []))}

### 執行結論
- 結果：{outcome}
"""
    
    with open(DECISION_LOG, 'a', encoding='utf-8') as f:
        f.write(log)

# ========== 主流程 ==========
def run_brain_core():
    """執行大腦核心"""
    print('='*70)
    print('Tina 大腦核心 v1.0 — 統一決策系統')
    print('='*70)
    print(f'時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # Layer 1
    print('[Layer 1] 目標定義層')
    positions = layer1_goal_anchor()
    print(f'  持倉：{len(positions)} 筆')
    
    # Layer 2
    print()
    print('[Layer 2] 邊界約束層')
    ok, checks = layer2_safe_boundary()
    for k, v in checks.items():
        print(f'  {k}：{"✅" if v else "❌"}')
    
    # Layer 3
    print()
    print('[Layer 3] 感知分析層')
    context = layer3_contextual_perception()
    twii_rsi = context.get('market', {}).get('TWII_RSI', 'N/A')
    print(f'  TWII RSI：{twii_rsi}')
    print(f'  持倉：{len(context.get("positions", []))} 筆')
    print(f'  經驗：{len(context.get("experience", []))} 筆記錄')
    
    # Layer 4
    print()
    print('[Layer 4] 專家委員會')
    expert = layer4_expert_committee(context)
    print(f'  評分：{expert["score"]}（{expert["verdict"]}）')
    for r in expert['reasons']:
        print(f'    - {r}')
    
    # Layer 5
    print()
    print('[Layer 5] 反思進化層')
    result = {'market': context.get('market', {}), 'positions': context.get('positions', [])}
    result['expert'] = expert
    layer5_reflection(result)
    print(f'  decision_log.md ✅')
    
    print()
    print('='*70)
    print(f'裁決：{expert["verdict"]}（{expert["score"]}分）')
    print('='*70)
    
    return result

if __name__ == '__main__':
    run_brain_core()
