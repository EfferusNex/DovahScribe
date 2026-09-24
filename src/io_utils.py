import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from src.field_filter import FIELD_FILTERS, ALL_SUPPORTED_TYPES, get_fields_for_record


def has_cyrillic(text: str) -> bool:
    """Проверяет, содержит ли строка символы кириллицы."""
    return bool(re.search(r'[\u0400-\u04FF]', text))


def is_already_russian(text: str) -> bool:
    """
    Проверяет, переведена ли строка уже на русский язык.
    Если строка содержит преимущественно русские буквы и нет непереведенных английских слов.
    """
    if not has_cyrillic(text):
        return False
    cyrillic_chars = len(re.findall(r'[\u0400-\u04FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    # Если кириллицы значительно больше латиницы или латиницы вообще нет
    return cyrillic_chars > latin_chars * 2 or latin_chars == 0


def is_valid_string(text: str, allow_russian: bool = True) -> bool:
    """
    Проверяет, требует ли строка обработки / перевода.
    Отсеивает:
      - Пустые строки и пробелы
      - Строки из одних цифр, спецсимволов и пунктуации
      - Технические пути (Meshes, Textures, Scripts, *.nif, *.dds, *.pex, *.psc)
      - Служебные переменные скриптов или идентификаторы с суффиксами
      - Уже переведенные русские строки (только если allow_russian=False)
    """
    if not text or not isinstance(text, str):
        return False

    trimmed = text.strip()
    if not trimmed:
        return False

    # 1. Отсеиваем строки только из цифр и спецсимволов
    if re.match(r'^[\d\s\W_]+$', trimmed):
        return False

    # 2. Отсеиваем файловые и системные пути
    if re.search(r'\.(nif|dds|pex|psc|wav|xwm|fuz|hkx|tri|bik|swf)$', trimmed, flags=re.IGNORECASE):
        return False
    if re.match(r'^(textures|meshes|scripts|sound|music|interface|seq|strings)[\/\\]', trimmed, flags=re.IGNORECASE):
        return False

    # 3. Отсеиваем явные скриптовые идентификаторы и служебные теги без текста
    if re.match(r'^[a-zA-Z0-9_]+_Script$', trimmed) or re.match(r'^<.+>$', trimmed):
        return False

    # 4. Если allow_russian=False и строка уже на русском — отсеиваем
    if not allow_russian and is_already_russian(trimmed):
        return False

    return True


def build_housecarl_records_params(
    plugin_name: str,
    types: Optional[List[str]] = None,
    limit: int = 50000,
    to_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Формирует словарь параметров для вызова MCP инструмента housecarl_records.
    Если указан to_file, housecarl выгружает полный дамп без усечения страниц.
    """
    target_types = types or ALL_SUPPORTED_TYPES
    
    # Собираем объединение всех нужных полей
    unique_fields = set()
    for t in target_types:
        for f in get_fields_for_record(t):
            unique_fields.add(f)

    params: Dict[str, Any] = {
        "plugins": {"names": [plugin_name]},
        "source": plugin_name,
        "types": target_types,
        "project": {
            "form": "fields",
            "fields": sorted(list(unique_fields)),
            "depth": 3,
        },
        "format": "json",
        "limit": limit,
    }
    if to_file:
        params["to_file"] = str(Path(to_file).resolve()).replace("\\", "/")

    return params


TRANSLATABLE_BASE_PATHS = {
    "Name", "Description", "Prompt", "ShortName", "BookText", "ActivateTextOverride",
    "MapMarker.Name", "MapMarker.Name.String"
}

METADATA_PATHS = {
    "Configuration.Flags", "Race", "Voice", "Speaker", "Conditions", "EditorID",
    "Responses", "Objectives", "Stages", "MenuButtons"
}


def is_translatable_path(path: str) -> bool:
    """Проверяет, является ли путь к полю транслируемым текстом, а не метаданными."""
    if path in METADATA_PATHS or path.startswith("*parent"):
        return False
    if path in TRANSLATABLE_BASE_PATHS:
        return True
    # Диалоговые реплики: Responses[0].Text
    if re.match(r"^Responses\[\d+\]\.Text$", path):
        return True
    # Кнопки сообщений: MenuButtons[0].Text
    if re.match(r"^MenuButtons\[\d+\]\.Text$", path):
        return True
    # Цели квестов: Objectives[0].DisplayText / Text
    if re.match(r"^Objectives\[\d+\]\.(DisplayText|Text)$", path):
        return True
    # Стадии квестов: Stages[0].LogEntry / Text
    if re.match(r"^Stages\[\d+\]\.(LogEntry|Text)$", path):
        return True
    return False


def parse_extracted_records(housecarl_json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Преобразует сырой ответ от housecarl_records в структурированный список строк для перевода.
    
    Каждый элемент содержит:
      - formid: FormID записи
      - type: тип записи (Armor, Weapon, DialogResponses, Book и т.д.)
      - editorid: EditorID (если есть)
      - path: точный путь к полю (Name, Description, BookText, Responses[0].Text)
      - text: оригинальный текст
      - parent_context: контекст предка (topic_id, topic_name) для связности диалогов
      - speaker_context: контекст говорящего и адресата (роль, пол, имя)
    """
    records = housecarl_json_data.get("records") or housecarl_json_data.get("matches") or []
    extracted_items: List[Dict[str, Any]] = []

    for rec in records:
        formid = rec.get("formid", "")
        rec_type = rec.get("type", "UNKNOWN")
        editorid = rec.get("editorid") or ""
        fields = rec.get("fields", [])

        # Извлекаем метаданные предка (*parent.EditorID, *parent.Name), если они есть
        parent_topic_id = ""
        parent_topic_name = ""
        for f in fields:
            f_path = f.get("path", "")
            if f_path == "*parent.EditorID" and "value" in f:
                parent_topic_id = f["value"]
            elif f_path == "*parent.Name" and "value" in f:
                parent_topic_name = f["value"]

        # Извлекаем текстовые поля для перевода
        for f in fields:
            f_path = f.get("path", "")
            if not is_translatable_path(f_path):
                continue  # Пропускаем метаданные при извлечении целевого текста

            raw_val = f.get("value")
            if raw_val and isinstance(raw_val, str) and is_valid_string(raw_val):
                extracted_items.append({
                    "formid": formid,
                    "type": rec_type,
                    "editorid": editorid,
                    "path": f_path,
                    "text": raw_val,
                    "fields": fields,  # Сохраняем поля для анализа контекста
                    "parent_context": {
                        "topic_id": parent_topic_id,
                        "topic_name": parent_topic_name,
                    } if (parent_topic_id or parent_topic_name) else {},
                })

    # Обогащаем записи контекстом спикера и пола
    try:
        from src.speaker_analyzer import SpeakerAnalyzer
        extracted_items = SpeakerAnalyzer.enrich_items_with_speaker_context(extracted_items, raw_records=records)
    except Exception:
        pass

    return extracted_items


def save_extracted_data(data: List[Dict[str, Any]], filepath: str):
    """Сохраняет извлеченные данные в JSON."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_extracted_data(filepath: str) -> List[Dict[str, Any]]:
    """Загружает ранее извлеченные данные из JSON или JSONL (от артефактов houseCARL)."""
    p = Path(filepath)
    if not p.exists():
        return []

    if p.suffix.lower() == ".jsonl":
        records = []
        with open(p, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    obj = json.loads(line_str)
                    # Первая строка в jsonl артефакте housecarl — манифест, пропускаем ее
                    if idx == 0 and "identity" in obj:
                        continue
                    records.append(obj)
                except Exception:
                    continue
        return parse_extracted_records({"records": records})
    else:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return parse_extracted_records(data)
