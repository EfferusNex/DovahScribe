import sys
import io
import json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.io_utils import is_valid_string, parse_extracted_records, build_housecarl_records_params
from src.field_filter import ALL_SUPPORTED_TYPES

def test_extraction_pipeline():
    print("🐾 === ТЕСТ ЭКСТРАКТОРА RAW ДАННЫХ ИЗ HOU бинарных записей ===")

    # 1. Проверяем построитель параметров houseCARL
    params = build_housecarl_records_params("Damsels in Distress.esp")
    print(f"\n[1] Сгенерированы параметры для housecarl_records:")
    print(f"    Плагин: {params['plugins']['names']}")
    print(f"    Отслеживаемые типы: {len(params['types'])} типов")
    print(f"    Целевые поля: {params['project']['fields']}")

    # 2. Проверяем парсер на реальных сырых записях
    sample_housecarl_data = {
        "records": [
            {
                "formid": "000849:Damsels in Distress.esp",
                "type": "Armor",
                "editorid": "damsel0_FalmerSkirt",
                "fields": [
                    {"path": "Name", "value": "Falmer Slave Skirt"},
                    {"path": "Description", "value": ""},
                ]
            },
            {
                "formid": "000847:Damsels in Distress.esp",
                "type": "Book",
                "editorid": "damsel0_VeilNote",
                "fields": [
                    {"path": "Name", "value": "Last Warning"},
                    {"path": "BookText", "value": "<font face='$HandwrittenFont'>I told you to stop!</font>"},
                ]
            },
            {
                "formid": "000907:Damsels in Distress.esp",
                "type": "DialogResponses",
                "editorid": None,
                "fields": [
                    {"path": "Responses[0].Text", "value": "Huh...? You're not a Forsworn."},
                    {"path": "Responses[1].Text", "value": "Are you here to save me?"},
                    {"path": "*parent.EditorID", "value": "damsel0_QuestRescue_LunaBranch01Topic"},
                    {"path": "*parent.Name", "value": "Are you alright?"}
                ]
            },
            {
                "formid": "000999:Damsels in Distress.esp",
                "type": "Armor",
                "editorid": "damsel0_AlreadyTranslated",
                "fields": [
                    {"path": "Name", "value": "Броня Изгоя"},  # Уже на русском!
                    {"path": "Description", "value": "12345"},    # Мусор (только цифры)
                ]
            }
        ]
    }

    extracted = parse_extracted_records(sample_housecarl_data)
    print(f"\n[2] Результат парсинга сырых записей (извлечено {len(extracted)} валидных строк):")
    for idx, item in enumerate(extracted, 1):
        parent_info = f" (Родительский топик: '{item['parent_context']['topic_name']}')" if item.get("parent_context") else ""
        print(f"    {idx}. [{item['type']} -> {item['path']}] {item['text']}{parent_info}")

    # Проверки ассертами
    texts = [x["text"] for x in extracted]
    assert "Falmer Slave Skirt" in texts
    assert "Last Warning" in texts
    assert "Huh...? You're not a Forsworn." in texts
    assert "Are you here to save me?" in texts
    assert "Броня Изгоя" not in texts, "Русская строка должна была отсеяться!"
    assert "12345" not in texts, "Мусорная строка должна была отсеяться!"

    print("\n✨ Все ассерты пройдены! Экстрактор и фильтры работают безупречно! 🐾")

if __name__ == "__main__":
    test_extraction_pipeline()
