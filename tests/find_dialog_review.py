import json

with open("data/review/Rafaela_review.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for entry in data["entries"]:
    t = entry.get("type")
    fld = entry.get("field")
    if t in ["Npc", "NPC_", "DialogResponses", "DialogTopic", "INFO", "DIAL"] or fld == "Prompt":
        print(f"ID {entry['id']} [{t}] {entry['formid']} ({fld}): {entry['original']}")
        print(f"  Speaker: {entry.get('speaker')}")
        print(f"  Context: {entry.get('speaker_context')}")
