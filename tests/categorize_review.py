import json
from collections import defaultdict

with open("data/review/ForgottenMagic_Redone_review.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entries", [])
categories = defaultdict(list)

for e in entries:
    categories[f"{e['type']}:{e['field']}"].append(e)

print(f"Total entries: {len(entries)}")
for cat, items in categories.items():
    print(f"\n--- {cat} ({len(items)} items) ---")
    for item in items[:5]:
        print(f"  [{item['formid']}] {item['original'][:70]}")
