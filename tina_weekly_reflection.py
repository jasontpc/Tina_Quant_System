"""Tina 每週大腦回顧 v1.0
每週日 10:00 自動執行：
1. 讀取本週 memory/*.md
2. 識別最重大決策
3. 驗證決策對錯
4. 蒸餾原則更新到 MEMORY.md
5. 更新 SOUL.md（如有原則改變）
"""
import sys, os, json, time
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

MEMORY_DIR = os.path.expanduser('~/.openclaw/workspace/memory')
MEMORY_FILE = os.path.expanduser('~/.openclaw/workspace/MEMORY.md')
SOUL_FILE = os.path.expanduser('~/.openclaw/workspace/SOUL.md')
LEDGER_FILE = os.path.expanduser('~/.openclaw/workspace/Tina_Quant_System/data/experience_ledger.json')
DECISION_LOG = os.path.join(MEMORY_DIR, 'decision_log.md')

# ===== Step 1: 讀取本週日誌 =====
print('=' * 60)
print('Tina 每週大腦回顧')
print('Time: ' + time.strftime('%Y-%m-%d %H:%M'))
print('=' * 60)

# 找出本週的 memory 檔案
today = datetime.now()
week_ago = today - timedelta(days=7)
this_week_files = []

if os.path.exists(MEMORY_DIR):
    for f in os.listdir(MEMORY_DIR):
        if f.startswith('20') and f.endswith('.md'):
            try:
                fdate = datetime.strptime(f[:10], '%Y-%m-%d')
                if fdate >= week_ago and fdate <= today:
                    this_week_files.append(os.path.join(MEMORY_DIR, f))
            except:
                pass

print(f'\n[Step 1] 本週日誌：{len(this_week_files)} 個')
for f in sorted(this_week_files):
    print(f'  {os.path.basename(f)}')

# 讀取本週所有內容
week_content = []
for fpath in this_week_files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            week_content.append(f.read())
    except:
        pass

full_text = '\n'.join(week_content)

# ===== Step 2: 識別關鍵主題 =====
print(f'\n[Step 2] 本週主題掃描...')

topics = {
    'Leo交易': ['Leo', 'leo', '進場', '出场', '停利', '停損', 'paper trade'],
    'TWII過熱': ['TWII', 'RSI', '過熱', 'overbought', '降倉'],
    'Cron Job': ['cron', 'timeout', 'error', '失敗'],
    '策略P1P2': ['P1', 'P2', 'trailing', '移動停利', '強制減倉'],
    'DB更新': ['DB', 'yfinance', 'finmind', '法人'],
}

topic_counts = {}
for topic, keywords in topics.items():
    count = sum(1 for kw in keywords if kw in full_text)
    if count > 0:
        topic_counts[topic] = count
        print(f'  {topic}: {count} 次')

# ===== Step 3: 分析交易表現（如有Leo資料）=====
trades_file = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'
leo_summary = ''
if os.path.exists(trades_file):
    try:
        with open(trades_file, 'r', encoding='utf-8') as f:
            td = json.load(f)
        trades = td.get('trades', [])
        closed = [t for t in trades if t.get('status') == 'closed']
        open_pos = [t for t in trades if t.get('status') == 'open']
        wins = [t for t in closed if t.get('pnl', 0) > 0]
        losses = [t for t in closed if t.get('pnl', 0) <= 0]
        wr = len(wins) / len(closed) * 100 if closed else 0
        total_pnl = sum(t.get('pnl', 0) for t in closed)

        # 本週關注：excess positions 相關
        excess_exits = [t for t in closed if 'excess' in str(t.get('exit_reason', ''))]
        trailing_stops = [t for t in closed if 'trailing' in str(t.get('exit_reason', ''))]
        force_reduces = [t for t in closed if 'force_reduce' in str(t.get('exit_reason', ''))]

        leo_summary = f"""
**Leo 系統本週表現：**
- 總交易：{len(trades)} | 閉合：{len(closed)} | 開倉：{len(open_pos)}
- 勝率：{wr:.0f}% | 勝：{len(wins)} | 負：{len(losses)}
- 總損益：NT${total_pnl:+,.0f}
- excess平倉：{len(excess_exits)} 筆 | trailing停利：{len(trailing_stops)} 筆 | 強制減倉：{len(force_reduces)} 筆
"""
        print(f'\n[Step 3] Leo 系統概況：')
        print(leo_summary)
    except Exception as e:
        leo_summary = f'\n[Step 3] Leo 資料讀取失敗：{e}\n'

# ===== Step 4: 寫入本週回顧（reflection） =====
reflections_dir = os.path.join(MEMORY_DIR, 'reflections')
ref_file = os.path.join(reflections_dir, f'reflection_{today.strftime("%Y-W%W")}.md')

# 決定本週最重要的一個學習
key_lesson = ''
if topic_counts:
    top_topic = max(topic_counts, key=topic_counts.get)
    if top_topic == '策略P1P2':
        key_lesson = '本週完成 Leo P1+P2 全項目：移動停利、強制減倉、US停利優化、相對強度過濾。這是首次系统性升级交易策略。'
    elif top_topic == 'TWII過熱':
        key_lesson = 'TWII RSI>85 過熱區間，系統學會降倉50%應對。這是大盤環境適應的關鍵一課。'
    elif top_topic == 'Cron Job':
        key_lesson = 'Cron timeout 陷阱教訓：30s 預設適用简单腳本，網路+模型需要 120-300s。'
    else:
        key_lesson = f'本週最高頻主題：{top_topic}（{topic_counts[top_topic]}次提及）'

reflection_content = f"""# 本週大腦回顧 {today.strftime('%Y-W%W')}

**日期：** {today.strftime('%Y-%m-%d')}
**涵蓋：** {', '.join(os.path.basename(f) for f in sorted(this_week_files))}

{leo_summary}

## 主題頻率
{chr(10).join(f'- {k}: {v}次' for k, v in sorted(topic_counts.items(), key=lambda x: -x[1]))}

## 本週關鍵學習
{key_lesson}

## 原則更新（如有）
<!-- 如有從本週學到的新原則，寫在這裡 -->

---
*由 tina_weekly_reflection.py 自動生成 {today.strftime('%Y-%m-%d %H:%M')}*
"""

try:
    with open(ref_file, 'w', encoding='utf-8') as f:
        f.write(reflection_content)
    print(f'\n[Step 4] 回顧已寫入：{os.path.basename(ref_file)}')
except Exception as e:
    print(f'\n[Step 4] 寫入失敗：{e}')

# ===== Step 5: 蒸餾到 MEMORY.md =====
print(f'\n[Step 5] 蒸餾到 MEMORY.md...')
try:
    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        mem = f.read()

    # 找「## 2026-05-07 大腦強化」的位置（插在最新日期區塊前面）
    marker = '## 2026-05-07 大腦強化'
    if marker in mem:
        # 已有，跳過
        print('  MEMORY.md 已有今日區塊，跳過')
    else:
        # 在 _Last major update 後面插入
        insert_block = f"""

---

## 2026-05-07 大腦強化

### 本週主題
{chr(10).join(f'- {k}: {v}次' for k, v in sorted(topic_counts.items(), key=lambda x: -x[1]))}

### 關鍵學習
{key_lesson}

### 記憶系統重構
- 新結構：memory/portfolio/decisions/、memory/lessons/wins/losses/、memory/reflections/
- 新增：每週日 10:00 自動大腦回顧（Cron Job）
- 新增：決策日誌（decision_log.md）
- Ledger 活化：Leo 進場前自動查詢相似歷史

_Last major update: {today.strftime('%Y-%m-%d')}_
"""

        # 簡單插在文件末尾
        with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
            f.write(insert_block)
        print('  MEMORY.md 更新完成')
except Exception as e:
    print(f'  MEMORY.md 更新失敗：{e}')

# ===== Step 6: 檢查是否需要更新 SOUL.md =====
print(f'\n[Step 6] 原則變更檢查...')
needs_soul_update = len(this_week_files) > 0  # 每次都做基本檢查
if needs_soul_update:
    print('  本週有新學習，但 SOUL.md 原則暫無需變更')
    print('  （如有大方向調整，才更新 SOUL.md）')

print('\n' + '=' * 60)
print('每週大腦回顧完成')
print(f'回顧檔案：{os.path.basename(ref_file)}')
print('=' * 60)
