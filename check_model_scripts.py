import os

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"

MODELS = {
    "ray-v3.5": "ray-v3.5 (4B combat)",
    "ray-deep-v1": "ray-deep-v1 (7B deep)",
    "qwen2.5:7b": "qwen2.5:7b (7B macro)",
    "qwen3.5-4b-iq4xs": "qwen3.5-4b (4B backup)",
}

results = {}
for fn in os.listdir(AGENTS_DIR):
    if not fn.endswith('.py'):
        continue
    fp = os.path.join(AGENTS_DIR, fn)
    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    matched = set()
    for model in MODELS:
        if model in content:
            matched.add(model)
    if matched:
        results[fn] = list(matched)

print("=" * 70)
print("SCRIPT -> MODEL MAPPING")
print("=" * 70)
for model in MODELS:
    print(f"\n[{model}] ({MODELS[model]})")
    scripts = sorted(k for k, v in results.items() if model in v)
    for s in scripts:
        print(f"  {s}")
    print(f"  TOTAL: {len(scripts)} scripts")

print("\n" + "=" * 70)
print("MODEL DUTIES")
print("=" * 70)
print("""
[ray-v3.5] 4B VRAM=2.7GB
  - Combat model: ray_brain.py, llm_router.py, us_momentum.py
  - Trading hours: 09:00-13:30 / 21:30-04:00
  - Used by: daily_premarket.py, tina_bridge.py, ray_vram_cleaner.py

[ray-deep-v1] 7B VRAM=4.7GB
  - Deep reasoning: ray_logic_distiller.py, run_logic_distiller.py
  - Strategy analysis: ray_us_strategy_analysis.py
  - Self-fixing: ray_self_fixer.py
  - Training hours: 14:00-21:00

[qwen2.5:7b] 7B VRAM=4.7GB
  - Macro analysis: ray_us_premarket_macro.py (21:00)
  - Knowledge distillation: ray_knowledge_distiller.py (14:00)

[qwen3.5-4b-iq4xs] 4B VRAM=2.7GB
  - Backup model: mostly idle
  - Legacy: bilingual_modelfile_generator.py
""")

print("=" * 70)
print("CROSS-MODEL SCRIPTS (need optimization)")
print("=" * 70)
for fn, models in results.items():
    if len(models) > 1:
        print(f"  {fn}: {', '.join(models)}")