import json
from src.quality_gate import QualityGate

with open("data/review/QuickLootIE_review.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data["entries"]:
    issue = QualityGate.validate_entry(item)
    if issue:
        print(f"[{issue.issue_type}] {item.get('path')}: \"{item.get('original')}\" -> \"{item.get('translated')}\"")
        print(f"   Details: {issue.details}")
