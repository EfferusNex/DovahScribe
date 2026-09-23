import json
import re

with open("data/review/ForgottenMagic_Redone_review.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entries", [])
unique_names = set()
unique_descriptions = set()

for e in entries:
    orig = e.get("original", "").strip()
    field = e.get("field", "")
    t = e.get("type", "")

    if field == "Description":
        unique_descriptions.add(orig)
    elif field in ["Name", "ShortName"]:
        unique_names.add(orig)

print(f"Unique names: {len(unique_names)}")
print(f"Unique descriptions: {len(unique_descriptions)}")

with open("data/review/unique_names.txt", "w", encoding="utf-8") as f:
    for n in sorted(list(unique_names)):
        f.write(n + "\n")

with open("data/review/unique_descriptions.txt", "w", encoding="utf-8") as f:
    for d in sorted(list(unique_descriptions)):
        f.write(d + "\n")
