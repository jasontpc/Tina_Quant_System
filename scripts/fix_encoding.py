import re

# Read the file with UTF-8
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\decision_committee_vote.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix format_vote_card function
old_func = '''def format_vote_card(vote: Dict) -> str:
    """格式化單一投票內容"""
    member_info = MEMBERS.get(vote['member'], {})
    color  = member_info.get('color', '#888')
    role   = member_info.get('role', '')
    vote_t = vote['vote']
    icon   = {'agree': '[+]', 'disagree': '[-]', 'abstain': '[=]', 'watch': '[@]'}.get(vote_t, '[?]')
    conf   = vote.get('confidence', 0)

    icon_str = {
        'agree':    f'\\033[92m{icon}\\033[0m',
        'disagree': f'\\033[91m{icon}\\033[0m',
        'abstain':  f'\\033[90m{icon}\\033[0m',
        'watch':    f'\\033[93m{icon}\\033[0m',
    }.get(vote_t, icon)

    return (
        f"  {icon_str} **{vote['member']}**（{role}）\\n"
        f"     信心度：{conf}%\\n"
        f"     理由：{vote.get('reason', 'N/A')}\\n"
        f"     標籤：{', '.join(vote.get('tags', [])) or '無'}"
    )'''

new_func = '''def format_vote_card(vote: Dict) -> str:
    member_info = MEMBERS.get(vote['member'], {})
    vote_t = vote['vote']
    icon = {'agree': '[+]', 'disagree': '[-]', 'abstain': '[=]', 'watch': '[@]'}.get(vote_t, '[?]')
    icon_str = {
        'agree':    f'\\033[92m{icon}\\033[0m',
        'disagree': f'\\033[91m{icon}\\033[0m',
        'abstain':  f'\\033[90m{icon}\\033[0m',
        'watch':    f'\\033[93m{icon}\\033[0m',
    }.get(vote_t, icon)
    conf = vote.get('confidence', 0)
    reason = vote.get('reason', 'N/A')
    tags = ','.join(vote.get('tags', [])) or 'none'
    # ASCII-safe output
    return (
        f"  {icon_str} **{vote['member']}**\\n"
        f"     conf={conf}% | reason: {reason[:80]}\\n"
        f"     tags: {tags}"
    )'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("Replaced format_vote_card OK")
else:
    print("Could not find exact old_func match. Checking...")
    # Try to find just the function name
    if 'def format_vote_card' in content:
        print("Found function - will do targeted regex replace")
        # Use regex to replace just this function
        import re
        pattern = r'def format_vote_card\(vote: Dict\) -> str:.*?return \(.*?\)'
        # Actually let's just find and replace the Chinese strings directly
        content = content.replace('格式化單一投票內容', 'Format vote card')
        content = content.replace('信心度', 'conf')
        content = content.replace('理由', 'reason')
        content = content.replace('標籤', 'tags')
        content = content.replace('無', 'none')
        content = content.replace('（', '(').replace('）', ')')
        print("Replaced Chinese labels in-place")

# Write back
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\decision_committee_vote.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("File written")