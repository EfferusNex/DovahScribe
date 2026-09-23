import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('data/review/SexLabDefeat_review.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

pending = [e for e in data['entries'] if not e.get('translated')]
with open('data/pending_defeat.json', 'w', encoding='utf-8') as f:
    json.dump(pending, f, ensure_ascii=False, indent=2)

print(f"Dumped {len(pending)} pending items to data/pending_defeat.json")
