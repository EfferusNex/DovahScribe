import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

from src.vanilla_matcher import VanillaMatcher
from src.narrative_context import NarrativeContextBuffer
from src.io_utils import parse_extracted_records


def test_pipeline_stages():
    print("🐾 === ТЕСТ ЭТАПОВ 3 (VANILLA MATCHER) И 4 (NARRATIVE CONTEXT) ===\n")

    # [1] Тест Vanilla Matcher
    print("[1] Проверка загрузки официальных .STRINGS файлов Скайрима...")
    matcher = VanillaMatcher()
    print(f"    Загружено официальных строк из бинарников: {len(matcher.id_to_text)} записей.")

    # Добавим для проверки каноничную пару в словарь
    matcher.add_canonical_pair("Iron Sword", "Железный меч")
    matcher.add_canonical_pair("Gold", "Золото")
    matcher.save_dictionary()

    print(f"    Проверка матчинга 'Iron Sword': -> '{matcher.match('Iron Sword')}'")
    print(f"    Проверка матчинга 'Gold': -> '{matcher.match('Gold')}'")
    assert matcher.match("Iron Sword") == "Железный меч"

    # [2] Тест Narrative Context Buffer на реальных диалогах
    print("\n[2] Проверка контекстного буфера на репликах диалогов...")
    sample_dialogues = [
        {
            "id": 1,
            "formid": "000907:Damsels.esp",
            "type": "DialogResponses",
            "path": "Responses[0].Text",
            "text": "Huh...? You're not a Forsworn.",
            "parent_context": {
                "topic_id": "LunaTopic01",
                "topic_name": "Are you alright?"
            }
        },
        {
            "id": 2,
            "formid": "000907:Damsels.esp",
            "type": "DialogResponses",
            "path": "Responses[1].Text",
            "text": "Are you here to save me?",
            "parent_context": {
                "topic_id": "LunaTopic01",
                "topic_name": "Are you alright?"
            }
        },
        {
            "id": 3,
            "formid": "000909:Damsels.esp",
            "type": "DialogResponses",
            "path": "Responses[0].Text",
            "text": "Thank you! Please get me out of here!",
            "parent_context": {
                "topic_id": "LunaTopic01",
                "topic_name": "Are you alright?"
            }
        }
    ]

    buffer = NarrativeContextBuffer(window_size=2)
    packages = buffer.build_contextual_packages(sample_dialogues)

    print(f"    Сформировано контекстных пакетов: {len(packages)}")
    # Проверяем второй пакет (целевая строка: "Are you here to save me?")
    pkg2 = packages[1]
    print(f"\n    Пакет #2:")
    print(f"      Целевой текст: '{pkg2['target_text']}'")
    print(f"      Контекст ДО: {[c['text'] for c in pkg2['context_before']]}")
    print(f"      Контекст ПОСЛЕ: {[c['text'] for c in pkg2['context_after']]}")
    print(f"      Топик игрока: '{pkg2['scene_context']['topic_name']}'")

    assert len(pkg2["context_before"]) == 1
    assert pkg2["context_before"][0]["text"] == "Huh...? You're not a Forsworn."
    assert len(pkg2["context_after"]) == 1
    assert pkg2["context_after"][0]["text"] == "Thank you! Please get me out of here!"

    # [3] Проверка генерации структурированного промпта
    mod_context = {
        "description": "Мод на спасение пленниц из лагерей Изгоев",
        "lore": "Предел (Reach), Эпоха 4Э 201"
    }
    prompt = buffer.format_prompt_for_packages(packages, mod_context)
    print(f"\n[3] Фрагмент сгенерированного промпта для AI:\n{'-'*40}\n{prompt[:450]}...\n{'-'*40}")

    print("\n✨ Все этапы 3 и 4 успешно протестированы! Муррр! 🐾")


if __name__ == "__main__":
    test_pipeline_stages()
