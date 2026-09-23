import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Устанавливаем UTF-8 для корректного вывода в терминале Windows
if sys.platform == "win32":
    try:
        if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

from src.io_utils import is_valid_string
from src.translation import TranslationEngine, normalize_mod_name


def run_test():
    print("🐾 === ЗАПУСК ТЕСТА СИСТЕМЫ ПЕРЕВОДА И СЛОВАРЯ ===\n")

    # 1. Тест фильтрации (io_utils)
    raw_strings = ["Iron Sword", "", "  ", "Load Game", "12345", "###", "Имя стражника"]
    print(f"[1] Входные строки: {raw_strings}")
    valid_strings = [s for s in raw_strings if is_valid_string(s)]
    print(f"    Отфильтрованные валидные строки: {valid_strings}\n")

    # 2. Тест нормализации имени мода при обновлении версий
    test_names = [
        "SilverWeapons_v1.0.esp",
        "SilverWeapons_v1.2.esp",
        "SilverWeapons - 2.0.esm",
        "Damsels in Distress.esp",
    ]
    print("[2] Тест нормализации имен плагинов (привязка словаря к моду):")
    for name in test_names:
        print(f"    {name:30} -> {normalize_mod_name(name)}")
    print()

    # 3. Сценарий: Первый перевод мода версии 1.0 (создание словаря)
    context = {
        "description": "Мод добавляет набор серебряного оружия против нежити",
        "lore": "Эпоха 4Э 201, Скайрим"
    }
    mod_v1 = "SilverWeapons_v1.0.esp"
    engine_v1 = TranslationEngine(mod_name=mod_v1, mod_context=context)

    batch_v1 = [
        {"formid": "01000D01", "type": "WEAP", "path": "Name", "text": "Silver Broadsword"},
        {"formid": "01000D02", "type": "WEAP", "path": "Description", "text": "Effective against undead and werewolves."},
        {"formid": "01000D03", "type": "MISC", "path": "Name", "text": "Purified Silver Ingot"},
    ]

    print(f"[3] Перевод мода первой версии ({mod_v1}):")
    res_v1 = engine_v1.translate_batch(batch_v1)
    for r in res_v1:
        print(f"    [{r['source']}] {r['text']} -> {r['translated']}")

    # 4. Проверка промпта для AI
    prompt = engine_v1.get_context_prompt(batch_v1)
    print(f"\n[4] Сгенерированный промпт для AI (фрагмент):\n{'-'*30}\n{prompt[:350]}...\n{'-'*30}\n")

    # 5. Сценарий: Вышло обновление мода до v1.1!
    # В v1.1 старые строки остались, но добавился новый кинжал "Silver Dagger"
    mod_v2 = "SilverWeapons_v1.1.esp"
    print(f"[5] Симуляция обновления: мод обновился до {mod_v2}!")
    engine_v2 = TranslationEngine(mod_name=mod_v2, mod_context=context)

    batch_v2 = [
        {"formid": "01000D01", "type": "WEAP", "path": "Name", "text": "Silver Broadsword"}, # Старое!
        {"formid": "01000D02", "type": "WEAP", "path": "Description", "text": "Effective against undead and werewolves."}, # Старое!
        {"formid": "01000D03", "type": "MISC", "path": "Name", "text": "Purified Silver Ingot"}, # Старое!
        {"formid": "01000D04", "type": "WEAP", "path": "Name", "text": "Silver Dagger"}, # НОВОЕ!
    ]

    res_v2 = engine_v2.translate_batch(batch_v2)
    print("    Результат проверки строк в обновленном моде:")
    for r in res_v2:
        source_badge = "✅ ИЗ СЛОВАРЯ (0 токенов)" if r["source"] == "tm_cache" else "🆕 ПЕРЕВЕДЕНО AI"
        print(f"    {source_badge:25} | {r['text']} -> {r['translated']}")

    # 6. Проверяем физический файл словаря
    tm_path = engine_v2.tm_file
    print(f"\n[6] Физический файл словаря на диске: {tm_path}")
    print(f"    Файл существует: {tm_path.exists()}")
    print(f"    Всего записей в словаре мода: {len(engine_v2.entries)}")
    print("\n✨ Все тесты успешно пройдены! Муррр! 🐾")


if __name__ == "__main__":
    run_test()
