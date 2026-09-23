import json
from pathlib import Path

dump_path = Path("data/raw_extracted/Rafaela_full_dump.jsonl")
if dump_path.exists():
    with open(dump_path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            r_type = rec.get("type")
            if r_type in ["Npc", "NPC_"]:
                formid = rec.get("formid")
                editorid = rec.get("editorid")
                print(f"Type: {r_type}, FormID: {formid}, EditorID: {editorid}")
                for fld in rec.get("fields", []):
                    print(f"  {fld.get('path')}: {fld.get('value')}")
                print("-" * 50)
