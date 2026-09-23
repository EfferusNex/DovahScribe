import json
from pathlib import Path
from src.mcm_manager import MCMManager
from src.quality_gate import QualityGate

review_file = Path("data/review/UIExtensions_review.json")
data = json.loads(review_file.read_text(encoding="utf-8"))

DICTIONARY = {
    "ALL": "ВСЕ",
    "ALTERATION": "ИЗМЕНЕНИЕ",
    "ILLUSION": "ИЛЛЮЗИЯ",
    "DESTRUCTION": "РАЗРУШЕНИЕ",
    "CONJURATION": "КОЛДОВСТВО",
    "RESTORATION": "ВОССТАНОВЛЕНИЕ",
    "SHOUTS": "КРИКИ",
    "POWERS": "ТАЛАНТЫ",
    "ACTIVE EFFECTS": "АКТИВНЫЕ ЭФФЕКТЫ",
    "Alteration": "Изменение",
    "Conjuration": "Колдовство",
    "Destruction": "Разрушение",
    "Illusion": "Иллюзия",
    "Restoration": "Восстановление",
    "Novice ({})": "Новичок ({})",
    "Apprentice ({})": "Ученик ({})",
    "Adept ({})": "Адепт ({})",
    "Expert ({})": "Эксперт ({})",
    "Master ({})": "Мастер ({})",
    "Health Rate": "Скорость восстановления здоровья",
    "Magicka Rate": "Скорость восстановления магии",
    "Stamina Rate": "Скорость восстановления запаса сил",
    "Heal Rate Mult": "Множитель восстановления здоровья",
    "Magicka Rate Mult": "Множитель восстановления магии",
    "Stamina Rate Mult": "Множитель восстановления сил",
    "Combat Health Regen": "Регенерация здоровья в бою",
    "Combat Magicka Regen": "Регенерация магии в бою",
    "Combat Stamina Regen": "Регенерация сил в бою",
    "Damage Resistance": "Сопротивление урону",
    "Poison Resistance": "Сопротивление ядам",
    "Fire Resistance": "Сопротивление огню",
    "Electric Resistance": "Сопротивление электричеству",
    "Frost Resistance": "Сопротивление холоду",
    "Magic Resistance": "Сопротивление магии",
    "Disease Resistance": "Сопротивление болезням",
    "Unarmed Damage": "Урон без оружия",
    "Critical Chance": "Шанс критического удара",
    "Melee Damage": "Урон в ближнем бою",
    "Unarmed Damage Mult": "Множитель урона без оружия",
    "Damage": "Урон",
    "Bow Speed": "Скорость натяжения лука",
    "Speed": "Скорость",
    "Reach": "Дальность атаки",
    "Armor": "Броня",
    "Weight": "Вес",
    "Value": "Цена",
    "Warmth": "Тепло",
    "Coverage": "Защита от холода",
    "Soul": "Душа",
    "Gold": "Золото",
    "Level": "Уровень",
    "Favorites": "Избранное",
    "Sort": "Сортировка",
    "Filter": "Фильтр",
    "Search": "Поиск",
    "Select": "Выбрать",
    "Back": "Назад",
    "Cancel": "Отмена",
    "Accept": "Принять",
    "Reset": "Сброс",
    "Defaults": "По умолчанию",
    "Enabled": "Включено",
    "Disabled": "Отключено",
    "Yes": "Да",
    "No": "Нет",
    "On": "Вкл",
    "Off": "Выкл",
}

for e in data["entries"]:
    orig = e["original"].strip()
    if orig in DICTIONARY:
        e["translated"] = DICTIONARY[orig]
        e["source"] = "tm_approved"
    elif not e.get("translated"):
        e["translated"] = orig
        e["source"] = "keep_original"
    
    issue = QualityGate.validate_entry(e)
    if issue:
        e["quality_status"] = "warning"
        e["quality_issue"] = issue.details
    else:
        e["quality_status"] = "ok"
        e["quality_issue"] = ""

# Обновляем метаданные
ready_cnt = sum(1 for e in data["entries"] if e.get("quality_status") == "ok")
data["metadata"]["ready_count"] = ready_cnt
data["metadata"]["quality_summary"] = {
    "is_clean": ready_cnt == len(data["entries"]),
    "passed": ready_cnt,
    "warnings": len(data["entries"]) - ready_cnt
}

# Сохраняем обновленный ревью JSON
review_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Updated {review_file} (Чисто: {ready_cnt}/{len(data['entries'])})")

# Экспорт в _RUSSIAN.txt
out_mcm = MCMManager.export_russian_mcm(data["entries"], "UIExtensions")
print(f"Exported Russian MCM: {out_mcm}")

# Синхронизация персонального дашборда
template_path = Path("web/cat_dashboard.html")
target_ui_path = Path("web/UIExtensions_dashboard.html")
review_content = review_file.read_text(encoding="utf-8")
template_content = template_path.read_text(encoding="utf-8")
injected_html = template_content.replace(
    '<script id="preloaded-data" type="application/json"></script>',
    f'<script id="preloaded-data" type="application/json">\n{review_content}\n</script>'
)
target_ui_path.write_text(injected_html, encoding="utf-8")
print(f"Synced {target_ui_path}")
