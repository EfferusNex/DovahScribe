import json
import re

with open("data/review/ForgottenMagic_Redone_review.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entries", [])
book_titles = set()
for e in entries:
    if e.get("field") == "BookText":
        clean = re.sub(r'<[^>]+>', '', e["original"]).strip()
        lines = [line.strip() for line in clean.split('\n') if line.strip()]
        if lines:
            book_titles.add(lines[0])

print(f"Unique book titles in BookText ({len(book_titles)}):")
for b in sorted(list(book_titles)):
    print(f"  '{b}'")
