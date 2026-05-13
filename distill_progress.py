import sqlite3, os, json, sys, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()

print('=== 蒸餾進度檢查 ===')
print()

# 1. 黃金案例庫
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 0.8')
gold_08 = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 1.5')
gold_15 = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 1.8')
gold_18 = c.fetchone()[0]
print('1. 黃金案例庫（backtest_reports）')
print(f'   Sharpe > 0.8: {gold_08} 筆')
print(f'   Sharpe > 1.5: {gold_15} 筆')
print(f'   Sharpe > 1.8: {gold_18} 筆')
print()

# 2. distillation dataset
distill_path = 'ray_distill_weekly.jsonl'
if os.path.exists(distill_path):
    with open(distill_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f'2. 蒸餾資料集: {len(lines)} 筆')
    if lines:
        first = json.loads(lines[0])
        keys = list(first.keys())
        print(f'   keys: {keys}')
        print(f'   weight: {first.get("weight", "?")}')
else:
    print('2. 蒸餾資料集: 尚未建立')

distill_train = 'ray_distill_train.jsonl'
if os.path.exists(distill_train):
    with open(distill_train, 'r', encoding='utf-8') as f:
        lines2 = f.readlines()
    print(f'   ray_distill_train.jsonl: {len(lines2)} 筆')
else:
    print('   ray_distill_train.jsonl: 尚未建立')

print()

# 3. wisdom_corrections
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
total_corr = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8')
high_conf = c.fetchone()[0]
print(f'3. wisdom_corrections: {total_corr} 筆（高信心: {high_conf} 筆）')

# 4. wisdom_logs
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight >= 2.0')
high_w = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE passed=1 AND weight IS NOT NULL')
good_w = c.fetchone()[0]
print(f'4. wisdom_logs: 高權重(>=2.0)={high_w} | passed有weight={good_w}')

# 5. 模型狀態
print()
print('5. 模型蒸餾狀態：')
try:
    r = requests.get('http://localhost:11434/api/tags', timeout=5)
    models = r.json().get('models', [])
    for m in models:
        if 'ray' in m['name'].lower():
            mb = m.get('size', 0) // (1024**2)
            print(f'   {m["name"]}: {mb:.0f} MB')
except:
    pass

# 6. GPU
print()
print('6. GPU + 蒸餾環境：')
try:
    import torch
    print(f'   PyTorch: {torch.__version__}')
    print(f'   CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'   GPU: {torch.cuda.get_device_name(0)}')
except Exception as e:
    print(f'   PyTorch CUDA: {e}')

try:
    import unsloth
    print(f'   Unsloth: {unsloth.__version__}')
except Exception as e:
    print(f'   Unsloth: 未就緒（triton 版本衝突）')

print()
print('=== 蒸餾 Pipeline 狀態 ===')
print()
print('Step 1: 黃金案例挖掘（Sharpe>0.8）     [DONE]')
print('Step 2: 7B 深度修正（wisdom_corr）    [DONE]')
print('Step 3: 生成 JSONL 蒸餾資料集          [PENDING]')
print('Step 4: Unsloth 微調訓練                [BLOCKED - triton]')
print('Step 5: 部署新權重到 Ollama              [PENDING]')
print()

conn.close()