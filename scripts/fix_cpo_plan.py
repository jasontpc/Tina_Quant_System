with open('scripts/cpo_dev_plan.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace("info['schedule']", "info.get('schedule', info.get('trigger', 'event-driven'))")
with open('scripts/cpo_dev_plan.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixed')