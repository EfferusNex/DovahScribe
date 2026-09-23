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

from src.tag_masker import TagMasker
from src.ai_agent import AIAgentCoordinator
from src.review_manager import ReviewManager


def test_ai_agent_pipeline():
    print("🐾 === ТЕСТ ЭТАПА 5 (TAG MASKING, REVIEW MANAGER, BATCH STACKING) ===\n")

    # [1] Тест TagMasker (Маскирование и размаскирование тегов)
    original_tagged_text = "<font face='$HandwrittenFont'><font size='18'>Привет, <ALIAS=Player>! [pagebreak] Урон: %d</font></font>"
    print(f"[1] Исходный текст с тегами:\n    {original_tagged_text}")

    masked, tag_map = TagMasker.mask(original_tagged_text)
    print(f"\n    Замаскированный текст для AI:\n    {masked}")
    print(f"    Карта защищенных тегов: {tag_map}")

    # Симулируем перевод от AI (где AI перевел текст вокруг токенов)
    simulated_ai_translation = "[__TAG_0__][__TAG_1__]Здравствуйте, [__TAG_2__]! [__TAG_3__] Урон: [__TAG_4__][__TAG_5__][__TAG_6__]"
    restored = TagMasker.unmask(simulated_ai_translation, tag_map)
    print(f"\n    Восстановленный перевод с оригинальными тегами:\n    {restored}")

    assert "<ALIAS=Player>" in restored
    assert "<font face='$HandwrittenFont'>" in restored
    assert "[pagebreak]" in restored
    assert "%d" in restored

    # [2] Тест стеков чанков и подготовки батчей
    print("\n[2] Проверка интеллектуального разбиения на чанки (Chunk Stacks)...")
    sample_items = [
        {"id": 1, "type": "Armor", "path": "Name", "text": "Falmer Slave Skirt"},
        {"id": 2, "type": "DialogResponses", "path": "Responses[0].Text", "text": "Huh...? You're not a Forsworn.", "parent_context": {"topic_id": "Luna01", "topic_name": "Are you alright?"}},
        {"id": 3, "type": "DialogResponses", "path": "Responses[1].Text", "text": "Are you here to save me?", "parent_context": {"topic_id": "Luna01", "topic_name": "Are you alright?"}},
        {"id": 4, "type": "Book", "path": "BookText", "text": "<font size='18'>Secret Journal Entry</font>"},
    ]

    coordinator = AIAgentCoordinator(dialog_batch_size=2, generic_batch_size=2, book_batch_size=1)
    chunks = coordinator.split_into_chunks(sample_items)
    print(f"    Всего сформировано чанков: {len(chunks)}")
    for idx, c in enumerate(chunks, 1):
        types_in_chunk = [x['type'] for x in c]
        print(f"      Чанк #{idx}: {len(c)} записей -> {types_in_chunk}")

    # [3] Проверка подготовки батча и валидации ответа
    prompt_str, tag_maps = coordinator.prepare_batch_payload(chunks[1], mod_context={"description": "Test Mod"})
    print(f"\n[3] Сгенерированный батч промпт для чанка диалогов:\n{'-'*30}\n{prompt_str[:300]}...\n{'-'*30}")

    # Симулируем ответ от Леин
    ai_response = [
        {"id": 2, "translated": "А...? Ты не из Изгоев."},
        {"id": 3, "translated": "Ты здесь, чтобы спасти меня?"},
    ]

    updated_items, missing = coordinator.apply_translations_and_unmask(chunks[1], ai_response, tag_maps)
    print(f"    Успешно применены переводы для {len(updated_items)} строк, пропущено ID: {missing}")
    assert len(missing) == 0
    assert updated_items[0]["translated"] == "А...? Ты не из Изгоев."

    # [4] Тест ReviewManager (Экспорт файла для проверки человеком)
    print("\n[4] Проверка экспорта файла ревью для Сэмпая...")
    review_path = ReviewManager.export_for_review("SampleMod_Test", sample_items)
    print(f"    Файл ревью успешно создан: {review_path}")
    assert review_path.exists()

    loaded_entries = ReviewManager.load_reviewed_file(review_path)
    print(f"    Загружено записей из файла ревью: {len(loaded_entries)}")
    assert len(loaded_entries) == len(sample_items)
    print(f"    Пример записи в файле ревью:")
    print(f"      Оригинал: '{loaded_entries[1]['original']}'")
    print(f"      Перевод:  '{loaded_entries[1]['translated']}'")
    print(f"      Тема:     '{loaded_entries[1]['topic']}'")

    print("\n✨ Все тесты Этапа 5 успешно пройдены! Муррр! 🐾")


if __name__ == "__main__":
    test_ai_agent_pipeline()
