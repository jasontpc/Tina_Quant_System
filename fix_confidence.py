with open('ray_knowledge_distiller.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'def recalculate_confidence(axiom, n_wisdoms, n_backtests, n_failures_count, avg_sharpe):\n    """"依據數據質量重新計算信心度，防止模型給出整齊數字"""\n    base = 0.60  # 固定 base，防止模型給出虛高信心\n    # 數據量加成（每項只加一次，不累加）\n    if n_wisdoms >= 15: base += 0.08\n    elif n_wisdoms >= 8: base += 0.04\n    if n_backtests >= 10: base += 0.08\n    elif n_backtests >= 5: base += 0.04\n    if avg_sharpe > 1.5: base += 0.10\n    elif avg_sharpe > 1.0: base += 0.06\n    elif avg_sharpe > 0.5: base += 0.03\n    # 限制在 0.55-0.90（避免全 1.0 或全 0.5）\n    return min(max(base, 0.55), 0.90)'

new = 'def recalculate_confidence(axiom, n_wisdoms, n_backtests, n_failures_count, avg_sharpe):\n    """"依據數據質量重新計算信心度，防止模型給出整齊數字"""\n    base = 0.50\n    if n_wisdoms >= 15: base += 0.08\n    elif n_wisdoms >= 8: base += 0.04\n    if n_backtests >= 10: base += 0.08\n    elif n_backtests >= 5: base += 0.04\n    if avg_sharpe > 1.5: base += 0.10\n    elif avg_sharpe > 1.0: base += 0.06\n    elif avg_sharpe > 0.5: base += 0.03\n    if n_failures_count >= 5: base += 0.05\n    return min(max(base, 0.50), 0.90)'

if old in content:
    content = content.replace(old, new)
    with open('ray_knowledge_distiller.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('Not found')