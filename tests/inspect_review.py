import json
from collections import Counter

with open("data/review/ForgottenMagic_Redone_review.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entries", [])
print(f"Total entries: {len(entries)}")

types = Counter(e["type"] for e in entries)
print("By record type:", types)

fields = Counter(e["field"] for e in entries)
print("By field:", fields)

# Sample of descriptions and names
print("\nSample entries:")
for e in entries[:15]:
    print(f"[{e['type']}:{e['field']}] {e['original']}")
