import json
import re

with open("data/review/ForgottenMagic_Redone_review.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entries", [])
untranslated = []

for e in entries:
    trans = e.get("translated", "")
    orig = e.get("original", "")
    clean_trans = re.sub(r'<[^>]+>', '', trans)
    clean_trans = re.sub(r'\$[a-zA-Z0-9_]+', '', clean_trans)
    clean_trans = re.sub(r'p(Ring|Armor)[a-zA-Z0-9_]+', '', clean_trans)
    clean_trans = re.sub(r'vFaction', '', clean_trans)

    if re.search(r'[a-zA-Z]{2,}', clean_trans):
        untranslated.append(e)

print(f"Total untranslated or partially translated entries: {len(untranslated)}")
for u in untranslated[:30]:
    print(f"[{u['type']}:{u['field']}] '{u['original']}' -> '{u['translated']}'")
