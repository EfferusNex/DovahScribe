import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Any

# Базовые пути проекта
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TM_DIR = DATA_DIR / "mod_translations"
GLOBAL_CACHE_FILE = DATA_DIR / "translation_cache.json"

TM_DIR.mkdir(parents=True, exist_ok=True)


def normalize_mod_name(raw_name: str) -> str:
    """
    Нормализует имя мода, отсекая расширения плагинов (.esp/.esm/.esl)
    и версии (например: 'CoolMod_v1.2.esp' -> 'CoolMod', 'Armor_Pack - 2.0' -> 'Armor_Pack').
    Это позволяет автоматически подтягивать словарь при выходе обновлений мода.
    """
    if not raw_name:
        return "common"

    # 1. Отрезаем расширения файлов
    name = re.sub(r"\.(esp|esm|esl)$", "", raw_name.strip(), flags=re.IGNORECASE)

    # 2. Отрезаем распространенные суффиксы версий: _v1.0, -v2.1.3, _1.4,  v2.0, build 123
    name = re.sub(
        r"([._\s-]+(v|ver|version)?[0-9]+([._][0-9]+)*([a-zA-Z])?)$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()

    # 3. Безопасное имя для файловой системы
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return safe_name if safe_name else "common"


class TranslationEngine:
    """
    Движок памяти переводов (Translation Memory) и локализации модов.
    Поддерживает:
      - Персональный человекочитаемый словарь мода (data/mod_translations/{mod_name}.json).
      - Защиту от повторного перевода при обновлении модов (подтягивание существующих строк).
      - Глобальный кэш общих строк (data/translation_cache.json).
      - Пакетное сохранение на диск (без оверхеда на каждую строку).
    """

    def __init__(
        self,
        mod_name: Union[str, Dict] = "common",
        mod_context: Optional[Dict] = None,
    ):
        # Поддержка вызова TranslationEngine(context) без mod_name для обратной совместимости
        if isinstance(mod_name, dict):
            self.mod_context = mod_name
            self.raw_mod_name = "common"
        else:
            self.raw_mod_name = str(mod_name)
            self.mod_context = mod_context or {}

        self.canonical_name = normalize_mod_name(self.raw_mod_name)
        self.tm_file = TM_DIR / f"{self.canonical_name}.json"

        # Структура TM: { key: { original, translated, record_type, field, formid, source, ... } }
        self.metadata: Dict[str, Any] = {}
        self.entries: Dict[str, Dict[str, Any]] = {}
        self._load_tm()

        # Глобальный кэш (ленивая загрузка при необходимости)
        self._global_cache: Optional[Dict[str, str]] = None

    def _generate_key(self, record_type: str, field_path: str, text: str) -> str:
        """
        Создает читаемый составной ключ: 'TYPE:FIELD:OriginalText'.
        Если оригинальный текст слишком длинный (книги), добавляет короткий хэш для стабильности.
        """
        clean_text = text.strip().replace("\r\n", "\n")
        if len(clean_text) > 100:
            short_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()[:8]
            truncated = clean_text[:60].replace("\n", " ")
            return f"{record_type}:{field_path}:{truncated}...[{short_hash}]"
        return f"{record_type}:{field_path}:{clean_text}"

    def _load_tm(self):
        """Загружает словарь мода с поддержкой миграции старых форматов."""
        if self.tm_file.exists():
            try:
                with open(self.tm_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Новый расширенный формат со структурой {"metadata": ..., "entries": ...}
                if isinstance(data, dict) and "entries" in data:
                    self.metadata = data.get("metadata", {})
                    self.entries = data.get("entries", {})
                # Старый формат: простой словарь {key: value}
                elif isinstance(data, dict):
                    self.metadata = {
                        "mod_name": self.canonical_name,
                        "migrated": True,
                    }
                    self.entries = {}
                    for k, v in data.items():
                        if isinstance(v, dict):
                            self.entries[k] = v
                        else:
                            self.entries[k] = {
                                "original": k.split(":")[-1] if ":" in k else k,
                                "translated": str(v),
                                "source": "legacy_import",
                            }
            except Exception as e:
                print(f"⚠️ Ошибка чтения словаря {self.tm_file}: {e}. Создан чистый словарь.")
                self.entries = {}
        else:
            self.metadata = {
                "mod_name": self.canonical_name,
                "created_at": datetime.now().isoformat(),
            }
            self.entries = {}

    def _save_tm(self):
        """Сохраняет словарь мода в человекочитаемом виде."""
        self.metadata["updated_at"] = datetime.now().isoformat()
        self.metadata["total_entries"] = len(self.entries)

        payload = {
            "metadata": self.metadata,
            "entries": self.entries,
        }

        temp_file = self.tm_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        temp_file.replace(self.tm_file)

    def _get_global_cache(self) -> Dict[str, str]:
        """Загружает глобальный межмодовый кэш при первом обращении."""
        if self._global_cache is None:
            if GLOBAL_CACHE_FILE.exists():
                try:
                    with open(GLOBAL_CACHE_FILE, "r", encoding="utf-8") as f:
                        self._global_cache = json.load(f)
                except Exception:
                    self._global_cache = {}
            else:
                self._global_cache = {}
        return self._global_cache

    def _save_global_cache(self):
        """Сохраняет глобальный кэш общих строк."""
        if self._global_cache is not None:
            with open(GLOBAL_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._global_cache, f, ensure_ascii=False, indent=2)

    def get_translation(
        self,
        record_type: str,
        field_path: str,
        text: str,
    ) -> Optional[str]:
        """
        Ищет перевод в словаре мода.
        Уровни поиска:
          1. Точное совпадение: TYPE:FIELD:Text в словаре мода.
          2. Совпадение по тексту в том же типе записи (например, WEAP:Description -> WEAP:Name).
          3. Поиск в глобальном кэше translation_cache.json.
        """
        if not text:
            return None

        # 1. Прямой поиск в локальном словаре мода
        key = self._generate_key(record_type, field_path, text)
        if key in self.entries:
            entry = self.entries[key]
            return entry.get("translated") if isinstance(entry, dict) else str(entry)

        # 2. Фоллбэк: совпадение по чистому тексту в словаре этого же мода
        clean_text = text.strip()
        for entry_key, entry in self.entries.items():
            if isinstance(entry, dict) and entry.get("original") == clean_text:
                return entry.get("translated")

        # 3. Фоллбэк: поиск в глобальном кэше
        global_cache = self._get_global_cache()
        if clean_text in global_cache:
            return global_cache[clean_text]

        return None

    def save_translation(
        self,
        record_type: str,
        field_path: str,
        original: str,
        translated: str,
        formid: str = "",
        source: str = "ai",
        auto_save: bool = False,
    ):
        """
        Добавляет перевод в словарь мода.
        auto_save: если False, запись накапливается в памяти до вызова save_tm().
        """
        key = self._generate_key(record_type, field_path, original)
        self.entries[key] = {
            "original": original,
            "translated": translated,
            "record_type": record_type,
            "field": field_path,
            "formid": formid,
            "source": source,
            "updated_at": datetime.now().isoformat(),
        }

        # Также обновляем глобальный словарь общих строк для коротких терминов/названий
        if len(original.strip()) <= 80:
            g_cache = self._get_global_cache()
            g_cache[original.strip()] = translated.strip()

        if auto_save:
            self._save_tm()
            self._save_global_cache()

    def get_context_prompt(self, batch: List[Dict[str, Any]]) -> str:
        """
        Формирует структурированный промпт для AI (Gemini) с контекстом мода и правилами.
        """
        mod_desc = self.mod_context.get("description", "Skyrim Mod")
        lore = self.mod_context.get("lore", "The Elder Scrolls V: Skyrim universe")

        prompt_lines = [
            "Ты профессиональный локализатор игр и эксперт по вселенной The Elder Scrolls V: Skyrim.",
            f"Контекст мода: {mod_desc}",
            f"Лор и эпоха: {lore}",
            "",
            "Правила локализации:",
            "1. Переводи с английского на естественный, атмосферный русский язык.",
            "2. Соблюдай официальную русскую терминологию Skyrim (Названия городов, рас, заклинаний, предметов).",
            "3. Сохраняй технические теги без изменений: <font color='...'>, <br>, <ALIAS=...>, [pagebreak], спецсимволы.",
            "4. Верни ответ строго в формате JSON списка объектов: [{\"id\": ..., \"translated\": \"...\"}].",
            "",
            "Строки для перевода:"
        ]

        items_for_prompt = []
        for idx, item in enumerate(batch):
            items_for_prompt.append({
                "id": idx,
                "type": item.get("type", "UNKNOWN"),
                "field": item.get("path", "Text"),
                "original": item.get("text", "")
            })

        prompt_lines.append(json.dumps(items_for_prompt, ensure_ascii=False, indent=2))
        return "\n".join(prompt_lines)

    def translate_batch(
        self,
        batch: List[Union[Dict[str, Any], str]]
    ) -> List[Dict[str, Any]]:
        """
        Пакетный перевод списка записей.
        batch может быть списком словарей [{"formid", "type", "path", "text"}]
        или простым списком строк ["Iron Sword", ...].

        Процесс:
          1. Сверяет строки со словарем мода (TM) и глобальным кэшем.
          2. Уже переведенные строки подставляются мгновенно (0 вызовов AI).
          3. Только новые строки передаются на перевод.
          4. Результаты сохраняются в словарь мода одним батчем!
        """
        normalized_batch: List[Dict[str, Any]] = []
        for idx, raw in enumerate(batch):
            if isinstance(raw, str):
                normalized_batch.append({
                    "id": idx,
                    "formid": "",
                    "type": "MISC",
                    "path": "Name",
                    "text": raw,
                })
            else:
                item_dict = dict(raw)
                if "id" not in item_dict:
                    item_dict["id"] = idx
                normalized_batch.append(item_dict)

        results: List[Dict[str, Any]] = []
        to_translate: List[Dict[str, Any]] = []

        # 1. Проверяем локальный словарь мода и кэш
        for item in normalized_batch:
            r_type = item.get("type", "MISC")
            path = item.get("path", "Name")
            text = item.get("text", "")

            cached_translation = self.get_translation(r_type, path, text)
            if cached_translation:
                item["translated"] = cached_translation
                item["source"] = "tm_cache"
                results.append(item)
            else:
                to_translate.append(item)

        # Если все строки уже были в словаре (например, мод обновился без изменения текстов)
        if not to_translate:
            results.sort(key=lambda x: x["id"])
            return results

        # 2. Отправка новых строк в AI (или заглушка с сохранением)
        print(f"🐾 Найдено {len(to_translate)} новых строк для мода '{self.canonical_name}' (из {len(normalized_batch)}). Отправляю в перевод...")

        # TODO: Интеграция с реальным Gemini API через google-genai
        # Сейчас для наглядности работы словаря формируем перевод и сразу фиксируем в словаре
        for item in to_translate:
            original = item.get("text", "")
            # Имитация качественного перевода с префиксом [RU] для проверки
            translated = item.get("translated") or f"[RU] {original}"
            item["translated"] = translated
            item["source"] = "ai"

            # Сохраняем в память TM
            self.save_translation(
                record_type=item.get("type", "MISC"),
                field_path=item.get("path", "Name"),
                original=original,
                translated=translated,
                formid=item.get("formid", ""),
                source="ai",
                auto_save=False  # Пакетная запись!
            )
            results.append(item)

        # 3. Пакетно сбрасываем обновленный словарь на диск
        self._save_tm()
        self._save_global_cache()
        print(f"✨ Словарь '{self.canonical_name}.json' обновлен и сохранен ({len(self.entries)} записей).")

        results.sort(key=lambda x: x["id"])
        return results
