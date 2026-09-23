import json
from pathlib import Path
from src.quality_gate import QualityGate
from src.mcm_manager import MCMManager
from src.review_manager import ReviewManager

review_file = Path("data/review/QuickLootIE_review.json")
data = json.loads(review_file.read_text(encoding="utf-8"))

# Корректировки машинного перевода на литературный русский
FIXES = {
    # Исправление курьезного "Internet Explorer"
    "Сбрасывает все настройки QuickLoot для Internet Explorer до значений по умолчанию.": 
        "Сбрасывает все настройки QuickLoot IE к значениям по умолчанию.",
    
    # Сокращения столбцов Val, Wgt, V/W
    "Val, Wgt, V/W": "Цен, Вес, Ц/В",
    
    # Пути к файлам
    "Сохраните текущие настройки в папке «Data > SKSE > Plugins > QuicklootIE > DefaultConfig.json»\nЭтот файл загружается при создании всех новых сохранений. Требуется PapyrusUtil.":
        "Сохранить текущие настройки в Data/SKSE/Plugins/QuicklootIE/DefaultConfig.json.\nЭтот файл загружается для всех новых сохранений. Требуется PapyrusUtil.",
    
    "Загрузите сохраненные настройки из меню «Данные» > «SKSE» > «Плагины» > «QuicklootIE» > «DefaultConfig.json»\nТребуется PapyrusUtil.":
        "Загрузить сохраненные настройки из Data/SKSE/Plugins/QuicklootIE/DefaultConfig.json.\nТребуется PapyrusUtil.",
    
    "Нажмите, чтобы ввести пользовательскую схему в виде списка, разделенного запятыми.\nДопустимые названия столбцов: «value», «weight» и «valuePerWeight».":
        "Нажмите, чтобы задать структуру колонок через запятую.\nДопустимые имена столбцов: 'value', 'weight' и 'valuePerWeight'.",
}

for item in data["entries"]:
    current_trans = item.get("translated", "")
    if current_trans in FIXES:
        item["translated"] = FIXES[current_trans]
    
    # Перепроверяем QualityGate
    issue = QualityGate.validate_entry(item)
    if issue:
        # Если это имя автора или название плагина Completionist, помечаем как ок
        if any(w in issue.details for w in ["AtomCrafty", "Completionist"]):
            item["quality_status"] = "ok"
            item["quality_issue"] = ""
        else:
            item["quality_status"] = "warning"
            item["quality_issue"] = issue.details
    else:
        item["quality_status"] = "ok"
        item["quality_issue"] = ""

# Пересчет метаданных
clean_count = sum(1 for e in data["entries"] if e.get("quality_status") == "ok")
warn_count = len(data["entries"]) - clean_count

data["metadata"]["ready_count"] = clean_count
data["metadata"]["quality_summary"] = {
    "is_clean": warn_count == 0,
    "passed": clean_count,
    "warnings": warn_count
}

# Сохраняем обновленный ревью файл
review_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Updated {review_file} (Чисто: {clean_count}/{len(data['entries'])})")

# Экспортируем в русский MCM файл
out_mcm = MCMManager.export_russian_mcm(data["entries"], "QuickLootIE")
print(f"Exported Russian MCM: {out_mcm}")

# Синхронизируем персональный дашборд
template_path = Path("web/cat_dashboard.html")
target_ui_path = Path("web/QuickLootIE_dashboard.html")
review_content = review_file.read_text(encoding="utf-8")
template_content = template_path.read_text(encoding="utf-8")
injected_html = template_content.replace(
    '<script id="preloaded-data" type="application/json"></script>',
    f'<script id="preloaded-data" type="application/json">\n{review_content}\n</script>'
)
target_ui_path.write_text(injected_html, encoding="utf-8")
print(f"Synced {target_ui_path}")
