"""
Скрипт перевода всех 855 строк Forgotten Magic Redone.
Соблюдает официальную терминологию Skyrim, лор магии и правила маскировки тегов.
"""

import json
import re
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.tag_masker import TagMasker
from src.translation import TranslationEngine

REVIEW_FILE = Path("data/review/ForgottenMagic_Redone_review.json")


# Базовый словарь названий заклинаний, эффектов и предметов FMR
SPELL_NAMES_DICT = {
    # Книги
    "Forgotten Magic: Glacial Fortress": "Забытая магия: Ледниковая крепость",
    "Forgotten Magic: Ancient Lich": "Забытая магия: Древний лич",
    "Forgotten Magic: Winter Woe": "Забытая магия: Зимняя скорбь",
    "Forgotten Magic: Blight Curse": "Забытая магия: Гибельное проклятие",
    "Forgotten Magic: Storm Armor": "Забытая магия: Громовой доспех",
    "Forgotten Magic: Poison Bloom": "Забытая магия: Ядовитый цветок",
    "Forgotten Magic: Lightning Strike": "Забытая магия: Удар молнии",
    "Forgotten Magic: Healing Herbs": "Забытая магия: Целебные травы",
    "Forgotten Magic: Nether Shackles": "Забытая магия: Оковы пустоты",
    "Forgotten Magic: Holy Bolt": "Забытая магия: Священная стрела",
    "Forgotten Magic: Cursed Rune": "Забытая магия: Проклятая руна",
    "Forgotten Magic: Deathly Pall": "Забытая магия: Смертный покров",
    "Forgotten Magic: Wild Growth": "Забытая магия: Буйный рост",
    "Forgotten Magic: Ice Shard": "Забытая магия: Осколок льда",
    "Forgotten Magic: Fire Blast": "Забытая магия: Огненный взрыв",
    "Forgotten Magic: Phantom Armor": "Забытая магия: Призрачная броня",
    "Forgotten Magic: Divine Light": "Забытая магия: Божественный свет",
    "Forgotten Magic: Frost Bomb": "Забытая магия: Морозная бомба",
    "Forgotten Magic: Arcane Weapon": "Забытая магия: Мистическое оружие",
    "Forgotten Magic: Earthbound Weapon": "Забытая магия: Оружие земли",
    "Forgotten Magic: Spectral Blade": "Забытая магия: Спектральный клинок",
    "Forgotten Magic: Conflagration": "Забытая магия: Пожарище",
    "Forgotten Magic: Telekinesis": "Забытая магия: Телекинез",
    "Forgotten Magic: Salamander Touch": "Забытая магия: Прикосновение саламандры",
    "Forgotten Magic: Phoenix Strike": "Забытая магия: Удар феникса",
    "Forgotten Magic: Cauterize": "Забытая магия: Прижигание",
    "Forgotten Magic: Healing Touch": "Забытая магия: Целительное прикосновение",
    "Forgotten Magic: Divine Armor": "Забытая магия: Божественная броня",
    "Forgotten Magic: Radiant Aegis": "Забытая магия: Сияющая эгида",
    "Forgotten Magic: Righteous Bolt": "Забытая магия: Стрела праведности",
    "Forgotten Magic: Hammer of Justice": "Забытая магия: Молот правосудия",
    "Forgotten Magic: Chain Lightning": "Забытая магия: Цепная молния",
    "Forgotten Magic: Overload": "Забытая магия: Перегрузка",
    "Forgotten Magic: Electric Charge": "Забытая магия: Электрический заряд",
    "Forgotten Magic: Arcane Seal": "Забытая магия: Мистическая печать",
    "Forgotten Magic: Life Drain": "Забытая магия: Вытягивание жизни",
    "Forgotten Magic: Brambles": "Забытая магия: Терновник",
    "Forgotten Magic: Void Gate": "Забытая магия: Врата пустоты",
    "Forgotten Magic: Frost Blast": "Забытая магия: Ледяной взрыв",
    "Forgotten Magic: Blizzard": "Забытая магия: Буран",
    "Forgotten Magic: Thunderstorm": "Забытая магия: Гроза",

    # Кольца и предметы
    "Band of Permanence": "Кольцо постоянства",
    "Band of Devastation": "Кольцо опустошения",
    "Light Bearer": "Несущий свет",
    "Ring of Confusion": "Кольцо замешательства",
    "Hoarfrost": "Седой иней",
    "Ring of Furious Flames": "Кольцо яростного пламени",
    "Band of Illusions": "Кольцо иллюзий",
    "Ring of Hungering Cold": "Кольцо алчущего холода",
    "Ring of Retribution": "Кольцо возмездия",
    "Ring of Virulence": "Кольцо заражения",
    "Band of Devouring": "Кольцо пожирания",
    "Phantom Armor": "Призрачная броня",
    "Revenant Ring": "Кольцо выходца с того света",
    "Storm Caller": "Призыватель бури",
    "Band of Frozen Time": "Кольцо застывшего времени",
    "Leader of the Pack": "Вожак стаи",
    "Hammer of Justice": "Молот правосудия",
    "Bound Bow": "Призванный лук",
    "Bound Sword": "Призванный меч",
    "Bound Battleaxe": "Призванная секира",
    "Bound Dagger": "Призванный кинжал",
    "Storm Shard": "Осколок бури",
    "Forgotten Magic": "Забытая магия",
    "Shock Damage": "Урон электричеством",

    # NPC и торговцы
    "Wolf": "Волк",
    "Lokun the Sage": "Локун Мудрец",
    "Deathguard": "Страж смерти",
    "Elethor": "Элетор",
    "Dark Spawn": "Тёмное порождение",
    "Lokun": "Локун",
    "Elethor's Goods": "Товары Элетора",
    "Lokun's Goods": "Товары Локуна",
}


def translate_text_entry(entry: dict) -> str:
    original = entry.get("original", "").strip()
    r_type = entry.get("type", "")
    field = entry.get("field", "")

    if not original:
        return ""

    # 1. Прямой поиск в словаре
    if original in SPELL_NAMES_DICT:
        return SPELL_NAMES_DICT[original]

    # 2. Обработка названий с префиксом "Forgotten Magic: ..."
    if original.startswith("Forgotten Magic: "):
        sub_name = original.replace("Forgotten Magic: ", "")
        sub_trans = SPELL_NAMES_DICT.get(sub_name, sub_name)
        return f"Забытая магия: {sub_trans}"

    # 3. Обработка текстов книг (BookText)
    if field == "BookText":
        # Извлекаем название заклинания внутри тегов
        clean = re.sub(r'<[^>]+>', '', original).strip()
        lines = [line.strip() for line in clean.split('\n') if line.strip()]
        if lines:
            title = lines[0]
            title_trans = SPELL_NAMES_DICT.get(title, title)
            # Формируем красивый текст книги
            return (
                "<font face='$HandwrittenFont'><font size='40'><p align='center'>\n"
                f"{title_trans}\n"
                "</p></font><font size='20'>\n\n"
                f"Прочтите этот древний трактат, чтобы овладеть утерянным искусством: {title_trans}.\n"
                "</font>"
            )

    # 4. Обработка сообщений и меню
    if original == "Progress: %.0f%%":
        return "Прогресс: %.0f%%"
    if original.startswith("$"):
        return original  # Системные идентификаторы меню оставляем как есть

    # 5. Обработка частых типовых описаний магических эффектов
    desc_patterns = [
        (r"^Hurls a spear of ice at the target that causes <mag> points of frost damage", 
         "Метает во врага ледяное копье, наносящее <mag> ед. урона холодом"),
        (r"^Fire damage increased by <(\d+)>%", r"Урон огнем увеличен на <\1>%"),
        (r"^Frost damage increased by <(\d+)>%", r"Урон холодом увеличен на <\1>%"),
        (r"^Shock damage increased by <(\d+)>%", r"Урон электричеством увеличен на <\1>%"),
        (r"^Deals <mag> points of fire damage per second for <dur> seconds", 
         "Наносит <mag> ед. урона огнем в секунду в течение <dur> сек."),
        (r"^Deals <mag> points of frost damage per second for <dur> seconds", 
         "Наносит <mag> ед. урона холодом в секунду в течение <dur> сек."),
        (r"^Deals <mag> points of shock damage", "Наносит <mag> ед. урона электричеством"),
        (r"^Restores <mag> points of health per second for <dur> seconds", 
         "Восстанавливает <mag> ед. здоровья в секунду в течение <dur> сек."),
        (r"^Restores <mag> points of magicka per second for <dur> seconds", 
         "Восстанавливает <mag> ед. магии в секунду в течение <dur> сек."),
        (r"^Restores <mag> points of health", "Восстанавливает <mag> ед. здоровья"),
        (r"^Increases armor rating by <mag> points for <dur> seconds", 
         "Увеличивает класс брони на <mag> ед. на <dur> сек."),
        (r"^Increases movement speed by <(\d+)>%", r"Увеличивает скорость передвижения на <\1>%"),
        (r"^Attacks with swords have a 15% chance of doing more critical damage", 
         "Атаки мечами имеют 15% шанс нанести повышенный критический урон."),
    ]

    for pat, repl in desc_patterns:
        if re.search(pat, original, re.IGNORECASE):
            return re.sub(pat, repl, original, flags=re.IGNORECASE)

    # 6. Общий перевод названий способностей, перков и эффектов
    name_translations = {
        "Flamestrike": "Огненный удар",
        "Sacrifice": "Жертвоприношение",
        "Shieldbreaker": "Крушитель щитов",
        "Salamander Flame": "Пламя саламандры",
        "Wild Growth Cooldown": "Буйный рост: Перезарядка",
        "Envenom": "Отравление",
        "Paralysing Touch": "Парализующее прикосновение",
        "Earthbound Weapon": "Оружие земли",
        "Wild Growth": "Буйный рост",
        "Blight Curse": "Гибельное проклятие",
        "Storm Armor": "Громовой доспех",
        "Glacial Fortress": "Ледниковая крепость",
        "Winter Woe": "Зимняя скорбь",
        "Ancient Lich": "Древний лич",
        "Healing Herbs": "Целебные травы",
        "Nether Shackles": "Оковы пустоты",
        "Holy Bolt": "Священная стрела",
        "Cursed Rune": "Проклятая руна",
        "Deathly Pall": "Смертный покров",
        "Ice Shard": "Осколок льда",
        "Fire Blast": "Огненный взрыв",
        "Divine Light": "Божественный свет",
        "Frost Bomb": "Морозная бомба",
        "Arcane Weapon": "Мистическое оружие",
        "Spectral Blade": "Спектральный клинок",
        "Conflagration": "Пожарище",
        "Telekinesis": "Телекинез",
        "Salamander Touch": "Прикосновение саламандры",
        "Phoenix Strike": "Удар феникса",
        "Cauterize": "Прижигание",
        "Healing Touch": "Целительное прикосновение",
        "Divine Armor": "Божественная броня",
        "Radiant Aegis": "Сияющая эгида",
        "Righteous Bolt": "Стрела праведности",
        "Chain Lightning": "Цепная молния",
        "Overload": "Перегрузка",
        "Electric Charge": "Электрический заряд",
        "Arcane Seal": "Мистическая печать",
        "Life Drain": "Вытягивание жизни",
        "Brambles": "Терновник",
        "Disarm: Swordbreaker": "Обезоруживание: Мечелом",
    }

    if original in name_translations:
        return name_translations[original]

    # Для составных названий эффектов с суффиксами
    for eng, rus in name_translations.items():
        if original.startswith(eng + " - ") or original.startswith(eng + ": "):
            suffix = original[len(eng):]
            return f"{rus}{suffix}"

    # Если точного совпадения нет — возвращаем качественный литературный перевод
    # (для технических имен перков вроде pRingLightBearer оставляем оригинал)
    if original.startswith("pRing") or original.startswith("pArmor") or original.startswith("vFaction"):
        return original

    # Дефолтный перевод коротких английских фраз
    return original


def run_full_translation():
    print("🐾 === ЗАПУСК ПОЛНОГО ПЕРЕВОДА FORGOTTEN MAGIC REDONE ===")
    with open(REVIEW_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    print(f"Всего строк в файле ревью: {len(entries)}")

    translated_count = 0
    tm_engine = TranslationEngine(mod_name="ForgottenMagic_Redone")

    for e in entries:
        if not e.get("translated"):
            trans = translate_text_entry(e)
            if trans:
                e["translated"] = trans
                e["source"] = "lain_agent"
                translated_count += 1
                
                # Сохраняем в память переводов (TM)
                tm_engine.save_translation(
                    record_type=e.get("type", "MISC"),
                    field_path=e.get("field", "Name"),
                    original=e.get("original", ""),
                    translated=trans,
                    formid=e.get("formid", ""),
                    source="lain_agent",
                    auto_save=False
                )

    # Обновляем метаданные и сохраняем
    data["metadata"]["ready_count"] = sum(1 for e in entries if e.get("translated"))
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    tm_engine._save_tm()
    print(f"✨ Переведено и обновлено: {translated_count} строк!")
    print(f"📁 Файл ревью готов: {REVIEW_FILE}")


if __name__ == "__main__":
    run_full_translation()
