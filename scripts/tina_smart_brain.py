"""
Tina 智能大腦 - 互動記憶版
===========================
具備記憶提取能力的智能大腦
每次回應都會引用過去的經驗
"""

import os
import sys
from datetime import datetime

# 載入記憶管理模組
WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
sys.path.insert(0, WORKSPACE)
from scripts.tina_memory_manager import (
    build_memory_prompt,
    save_short_term_memory,
    save_experience,
    save_reflection,
    get_stock_experience,
    get_recent_reflections,
    get_user_preference,
    save_user_preference,
    get_tina_mood,
    save_proactive_action,
    init_memory_db
)

# ========== 核心分析函數 ==========
def tina_smart_brain(user_input, stock_id=None, session_id=None, health_score=5):
    """
    帶記憶的 Tina 智能大腦分析
    
    流程：
    1. 檢索相關歷史經驗
    2. 構建含記憶的 Prompt
    3. 生成回應（帶前情提要）
    4. 儲存對話到記憶
    """
    
    print('='*60)
    print('Tina Smart Brain - Interactive Memory Edition')
    print('='*60)
    print(f'[Input] {user_input}')
    print(f'[Stock] {stock_id or "N/A"}')
    print(f'[Health] {health_score}/5')
    print()
    
    # ========== 第一階段：記憶檢索 ==========
    print('[Phase 1] 檢索歷史經驗...')
    
    memory_context = build_memory_prompt(stock_id=stock_id, session_id=session_id)
    
    if memory_context:
        print('[OK] 找到相關記憶')
        print('-'*50)
        print(memory_context[:500])
        print('-'*50)
    else:
        print('[SKIP] 無相關歷史記憶')
    
    # ========== 第二階段：分析與回應生成 ==========
    print()
    print('[Phase 2] 生成分析...')
    
    # 語氣對齊
    mood = get_tina_mood(health_score)
    print(f'[Mood] {mood["tone"]} - {mood["prefix"]}')
    
    # 根據關鍵詞生成結構化分析
    response = generate_structured_response(user_input, stock_id, memory_context, mood)
    
    # ========== 第三階段：儲存記憶 ==========
    print()
    print('[Phase 3] 儲存記憶...')
    
    # 儲存對話到短期記憶
    action = extract_action(user_input)
    save_short_term_memory(
        session_id=session_id or 'default',
        user_input=user_input,
        tina_response=response['full_text'],
        stock=stock_id,
        action=action,
        result=response.get('outcome', 'pending')
    )
    
    # 如果有具體股票，儲存經驗
    if stock_id and action:
        save_experience(
            stock_id=stock_id,
            event_type=action,
            analysis_content=response.get('analysis', ''),
            decision=response.get('decision', ''),
            outcome=response.get('outcome', 'pending'),
            lessons=response.get('lessons', ''),
            confidence=health_score
        )
    
    # 儲存反思標籤
    if response.get('reflection'):
        save_reflection(
            session_id=session_id or 'default',
            stock_id=stock_id,
            reflection_text=response['reflection'],
            new_rule=response.get('new_rule', ''),
            mood_score=health_score
        )
    
    # ========== 輸出 ==========
    print()
    print('[Phase 4] 輸出回應')
    print('='*60)
    print(response['full_text'])
    print('='*60)
    
    return response

def generate_structured_response(user_input, stock_id, memory_context, mood):
    """生成結構化回應"""
    
    # 關鍵詞分析
    keywords = extract_keywords(user_input)
    is_stock_query = stock_id is not None
    is_action_request = any(word in user_input for word in ['買', '賣', '進場', '出场', '建議', '分析'])
    
    # 構建前情提要
    prelude = build_prelude(stock_id, memory_context)
    
    # 分析內容
    if is_stock_query:
        analysis = f"針對 {stock_id} 的技術分析"
    else:
        analysis = f"針對整體市場的分析"
    
    # 建議動作
    decision = "[分析中] 請稍候..."
    outcome = "pending"
    lessons = ""
    reflection = ""
    new_rule = ""
    
    # 根據查詢類型生成回應
    if is_action_request:
        decision = f"建議：觀察並等待更明確訊號"
        outcome = "action_pending"
    
    # 組合完整回應
    full_text = f"""{mood['prefix']}
{prelude}

{analysis}
-----------
{memory_context[:300] if memory_context else '[無歷史經驗參考]'}

建議動作：{decision}
{mood['suffix']}

<reflection>
今天學到：{reflection or '持續監控市場變化'}
</reflection>
"""
    
    return {
        'full_text': full_text.strip(),
        'prelude': prelude,
        'analysis': analysis,
        'decision': decision,
        'outcome': outcome,
        'lessons': lessons,
        'reflection': reflection,
        'new_rule': new_rule
    }

def build_prelude(stock_id, memory_context):
    """建立前情提要"""
    
    if not stock_id:
        return "基於目前的市場狀況，我來幫您分析："
    
    # 取得該股票的過去經驗
    past_exp = get_stock_experience(stock_id, limit=2)
    
    if past_exp:
        # 找到最新的經驗日期
        latest_date = past_exp[0][0]  # event_date
        prelude = f"基於我們在 {latest_date} 對 {stock_id} 的討論，我記得當時的分析結論是..."
        return prelude
    else:
        return f"針對 {stock_id} ，這是我第一次分析這個股票，讓我為您深入研究："

def extract_keywords(user_input):
    """提取關鍵詞"""
    words = []
    stocks = ['2330', '2382', '2454', '2881', '2883', '3231', 'DLO', 'RKLB', 'NVDA']
    
    for word in user_input.split():
        if word in stocks:
            words.append(word)
    
    return words

def extract_action(user_input):
    """提取用戶意圖"""
    if '分析' in user_input:
        return 'analysis'
    elif '建議' in user_input:
        return 'recommendation'
    elif '買' in user_input or '進場' in user_input:
        return 'buy_signal'
    elif '賣' in user_input or '出场' in user_input:
        return 'sell_signal'
    else:
        return 'general_query'

# ========== 主動行為觸發器 ==========
def check_proactive_trigger():
    """檢查是否需要主動發起"""
    
    # 檢查條件：
    # 1. 系統閒置 > 2小時
    # 2. 經驗庫有 > 3 條未總結記錄
    # 3. 尚未發送過
    
    print()
    print('[Proactive Check] 檢查主動行為條件...')
    
    recent_reflections = get_recent_reflections(hours=2)
    
    if len(recent_reflections) >= 3:
        print(f'[TRIGGER] 發現 {len(recent_reflections)} 條未總結經驗')
        
        # 生成進化週報
        report = generate_brain_evolution_report()
        
        # 記錄為待發送
        action_id = save_proactive_action('brain_evolution_report', report)
        
        print(f'[OK] 主動報告已記錄，ID: {action_id}')
        return report
    else:
        print(f'[SKIP] 條件不滿足（反思 {len(recent_reflections)} 條）')
        return None

def generate_brain_evolution_report():
    """生成大腦進化週報"""
    
    # 取得最近反思
    reflections = get_recent_reflections(hours=48)
    
    report = f"""🧠 Tina 大腦進化週報
========================
生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}

這兩天我學到了：

"""
    
    for ref in reflections:
        ts, sid, rtext, new_rule, mood = ref
        report += f"• {sid or '系統'}: {rtext}\n"
        if new_rule:
            report += f"  新規則：{new_rule}\n"
    
    report += f"""
目前反思總數：{len(reflections)} 條
系統健康度：5/5 ✅

主人，這是我這兩天學到的新東西，您有空可以聽聽我的彙報嗎？
"""
    
    return report

# ========== 測試 ==========
if __name__ == '__main__':
    print()
    print('='*60)
    print('Tina Smart Brain - Test Mode')
    print('='*60)
    print()
    
    # 初始化
    init_memory_db()
    
    # 測試1：一般查詢
    print('[Test 1] 一般市場查詢')
    print()
    tina_smart_brain('市場現在怎麼樣？', health_score=5)
    
    print()
    print()
    
    # 測試2：股票分析
    print('[Test 2] 2883 分析')
    print()
    tina_smart_brain('分析 2883', stock_id='2883', health_score=4)
    
    print()
    print()
    
    # 測試3：檢查主動行為
    print('[Test 3] 主動行為觸發檢查')
    check_proactive_trigger()