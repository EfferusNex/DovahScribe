import json
from pathlib import Path

raw_file = Path(r"C:\Users\Gettan\.gemini\antigravity-cli\brain\a43af68d-4dfc-46bc-84eb-a79cfc816435\.system_generated\steps\210\output.txt")
with open(raw_file, "r", encoding="utf-8") as f:
    raw = json.load(f)

records = raw.get("records", [])
print(f"Total records in raw: {len(records)}")

types = {}
value_fields = []
for r in records:
    t = r.get("type")
    types[t] = types.get(t, 0) + 1
    for f in r.get("fields", []):
        if "value" in f and f["value"]:
            value_fields.append((r["formid"], t, f["path"], f["value"]))

print("Types:", types)
print(f"Total value fields: {len(value_fields)}")
for formid, t, path, val in value_fields[:20]:
    print(f"  [{t}:{path}] {val[:60]}")
