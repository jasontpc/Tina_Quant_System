# Bulk replace FinMind token across all scripts
import os, glob

old_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM"
new_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8"

base = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
patterns = [
    os.path.join(base, "scripts", "*.py"),
    os.path.join(base, "teams", "**", "*.py"),
    os.path.join(base, "skills", "*.py"),
]
count = 0
for pat in patterns:
    for fp in glob.glob(pat, recursive=True):
        try:
            with open(fp, encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if old_token in content:
                new_content = content.replace(old_token, new_token)
                with open(fp, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated: {fp.replace(base, '')}")
                count += 1
        except Exception as e:
            print(f"Error {fp}: {e}")
print(f"Done: {count} files updated")