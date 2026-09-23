"""
🐾 Version Differ & Mod Update Backporter (Диффер версий модов).
Позволяет при выходе новой версии плагина:
  1. На 100% перенести готовые одобренные переводы без расхода токенов (0 токенов, 0 секунд).
  2. Трёхуровневый матчинг: FormID -> EditorID -> Text Invariant.
  3. Изолировать дельту: новые строки и модифицированные автором тексты.
  4. Для модифицированных строк передавать старый русский перевод в качестве подсказки (Memory Context).
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DiffEntry:
    item: Dict[str, Any]
    status: str  # 'reused_exact', 'reused_editor_id', 'reused_text', 'modified', 'new'
    reused_translation: Optional[str] = None
    previous_original: Optional[str] = None
    previous_translation: Optional[str] = None
    similarity: float = 1.0


@dataclass
class DiffReport:
    total_new_items: int = 0
    reused_count: int = 0
    modified_count: int = 0
    new_count: int = 0
    savings_percent: float = 0.0
    entries: List[DiffEntry] = field(default_factory=list)

    def summary(self) -> str:
        symbol = "🎉" if self.savings_percent > 50 else "🔄"
        return (
            f"{symbol} Отчёт сравнения версий:\n"
            f"   ├─ 📦 Всего строк в новой версии: {self.total_new_items}\n"
            f"   ├─ ⚡ Автоматически перенесено (0 токенов): {self.reused_count} ({self.savings_percent:.1f}%)\n"
            f"   ├─ 📝 Модифицировано автором: {self.modified_count}\n"
            f"   └─ ✨ Абсолютно новых строк: {self.new_count}"
        )


class VersionDiffer:
    """
    Модуль сравнения версий модов и мгновенного переноса готовых переводов.
    """

    @classmethod
    def load_entries_from_source(cls, source: Any) -> List[Dict[str, Any]]:
        """
        Загружает старые записи из файла ревью, словаря мода или переданного списка.
        """
        if isinstance(source, list):
            return source

        path = Path(source)
        if not path.exists():
            return []

        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(content, dict):
                if "entries" in content:
                    return content["entries"]
                if "translations" in content:
                    # Формат ModTranslationMemory
                    entries = []
                    for key, val in content.get("translations", {}).items():
                        entries.append({
                            "formid": key,
                            "original": val.get("original", ""),
                            "translated": val.get("translated", ""),
                            "field": val.get("field", "Name"),
                            "source": "tm"
                        })
                    return entries
            elif isinstance(content, list):
                return content
        except Exception as e:
            print(f"⚠️ Ошибка чтения файла старой версии {path}: {e}")

        return []

    @classmethod
    def compare_versions(
        cls,
        old_source: Any,
        new_items: List[Dict[str, Any]]
    ) -> DiffReport:
        """
        Сравнивает новую версию мода со старой и классифицирует каждую строку:
          - reused: точный перенос перевода (0 токенов);
          - modified: автор изменил текст (отправляется ИИ с контекстом старого перевода);
          - new: новая строка (отправляется ИИ на перевод).
        """
        old_entries = cls.load_entries_from_source(old_source)

        # 1. Индексация старой версии по ключам
        # FormID + Field
        by_formid_field: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # EditorID + Field
        by_editorid_field: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # Original Text Invariant (текст -> перевод)
        by_text: Dict[str, Dict[str, Any]] = {}

        for entry in old_entries:
            formid = str(entry.get("formid", "")).strip().lower()
            field_name = str(entry.get("field") or entry.get("path") or "Name").strip()
            editor_id = str(entry.get("editor_id") or entry.get("speaker_context", {}).get("editor_id") or "").strip().lower()
            orig = entry.get("original") or entry.get("text") or ""
            trans = entry.get("translated", "")

            # Нам нужны только записи с готовым переводом
            if not trans or not trans.strip():
                continue

            if formid:
                by_formid_field[(formid, field_name)] = entry
            if editor_id:
                by_editorid_field[(editor_id, field_name)] = entry
            if orig:
                by_text[orig.strip()] = entry

        # 2. Сопоставление новых элементов
        diff_entries: List[DiffEntry] = []
        reused_count = 0
        modified_count = 0
        new_count = 0

        for item in new_items:
            formid = str(item.get("formid", "")).strip().lower()
            field_name = str(item.get("path") or item.get("field") or "Name").strip()
            parent_ctx = item.get("parent_context") or {}
            editor_id = str(item.get("editor_id") or parent_ctx.get("editor_id") or "").strip().lower()
            orig = (item.get("text") or item.get("original") or "").strip()

            # Пропуск пустых строк
            if not orig:
                continue

            matched_entry: Optional[Dict[str, Any]] = None
            match_type: Optional[str] = None

            # Уровень 1: Точный FormID + Field
            if (formid, field_name) in by_formid_field:
                old_match = by_formid_field[(formid, field_name)]
                old_orig = (old_match.get("original") or old_match.get("text") or "").strip()
                if old_orig == orig:
                    matched_entry = old_match
                    match_type = "reused_exact"
                else:
                    # Тот же FormID, но автор изменил текст!
                    diff_entries.append(DiffEntry(
                        item=item,
                        status="modified",
                        previous_original=old_orig,
                        previous_translation=old_match.get("translated", "")
                    ))
                    modified_count += 1
                    continue

            # Уровень 2: Совпадение по EditorID + Field (если FormID сменился при перекомпиляции)
            if not matched_entry and editor_id and (editor_id, field_name) in by_editorid_field:
                old_match = by_editorid_field[(editor_id, field_name)]
                old_orig = (old_match.get("original") or old_match.get("text") or "").strip()
                if old_orig == orig:
                    matched_entry = old_match
                    match_type = "reused_editor_id"

            # Уровень 3: Точное совпадение уникального текста оригинала
            if not matched_entry and orig in by_text:
                old_match = by_text[orig]
                matched_entry = old_match
                match_type = "reused_text"

            if matched_entry and match_type:
                trans = matched_entry.get("translated", "")
                diff_entries.append(DiffEntry(
                    item=item,
                    status=match_type,
                    reused_translation=trans
                ))
                reused_count += 1
            else:
                diff_entries.append(DiffEntry(
                    item=item,
                    status="new"
                ))
                new_count += 1

        total_new = len(diff_entries)
        savings = (reused_count / total_new * 100.0) if total_new > 0 else 0.0

        return DiffReport(
            total_new_items=total_new,
            reused_count=reused_count,
            modified_count=modified_count,
            new_count=new_count,
            savings_percent=savings,
            entries=diff_entries
        )

    @classmethod
    def apply_diff_to_pipeline(
        cls,
        diff_report: DiffReport
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Разделяет список записей на:
          1. ready_items — строки, которые уже переведены (reused) с заполненным 'translated'.
          2. pending_items — строки, требующие доперевода (новые и модифицированные с контекстом).
        """
        ready_items: List[Dict[str, Any]] = []
        pending_items: List[Dict[str, Any]] = []

        for diff_entry in diff_report.entries:
            item = dict(diff_entry.item)

            if diff_entry.status.startswith("reused_"):
                item["translated"] = diff_entry.reused_translation
                item["source"] = f"backport_{diff_entry.status}"
                ready_items.append(item)
            elif diff_entry.status == "modified":
                item["previous_original"] = diff_entry.previous_original
                item["previous_translation"] = diff_entry.previous_translation
                item["source"] = "modified_pending"
                pending_items.append(item)
            else:  # 'new'
                item["source"] = "new_pending"
                pending_items.append(item)

        return ready_items, pending_items
