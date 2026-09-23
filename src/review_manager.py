import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.quality_gate import QualityGate, QualityReport

BASE_DIR = Path(__file__).resolve().parent.parent
REVIEW_DIR = BASE_DIR / "data" / "review"
REVIEW_DIR.mkdir(parents=True, exist_ok=True)


class ReviewManager:
    """
    Менеджер промежуточных файлов ревью и ручной проверки перевода.
    Формирует удобный, наглядный JSON-файл, в котором каждая запись содержит:
      - оригинальный английский текст;
      - предложенный вариант перевода (от Леин, TM или Strings);
      - метаданные (кто говорит, тема диалога, FormID, тип записи);
      - статус Quality Gate (контроль утечек английского и целостности тегов).
    
    Сэмпай может открыть этот файл, проверить или поправить перевод, 
    после чего изменения загружаются в патчер.
    """

    @classmethod
    def get_review_filepath(cls, mod_name: str) -> Path:
        clean_name = mod_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        return REVIEW_DIR / f"{clean_name}_review.json"

    @classmethod
    def export_for_review(
        cls,
        mod_name: str,
        items: List[Dict[str, Any]],
        filepath: Optional[Path] = None,
    ) -> Path:
        """
        Экспортирует список строк в наглядный файл для проверки человеком с Quality Gate аудитом.
        """
        out_path = Path(filepath) if filepath else cls.get_review_filepath(mod_name)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        review_entries = []
        for idx, item in enumerate(items, 1):
            parent_ctx = item.get("parent_context") or {}
            spk_ctx = item.get("speaker_context") or {}
            speaker = item.get("speaker") or spk_ctx.get("badge") or spk_ctx.get("speaker_name") or parent_ctx.get("speaker") or ""
            topic = parent_ctx.get("topic_name") or parent_ctx.get("topic_id") or ""

            entry = {
                "id": item.get("id", idx),
                "formid": item.get("formid", ""),
                "type": item.get("type", "UNKNOWN"),
                "field": item.get("path", "Name"),
                "speaker": speaker,
                "topic": topic,
                "speaker_context": spk_ctx,
                "original": item.get("text", ""),
                "translated": item.get("translated", ""),
                "source": item.get("source", "pending"),
            }

            # Проверка через Quality Gate
            issue = QualityGate.validate_entry(entry)
            if issue:
                entry["quality_status"] = "warning"
                entry["quality_issue"] = issue.details
                # Если была утечка английского в переведенном поле, помечаем источник
                if issue.issue_type in ["language_leak", "untranslated"] and entry["source"] not in ["vanilla", "vanilla_strings"]:
                    entry["source"] = "leak_detected"
            else:
                entry["quality_status"] = "ok"

            review_entries.append(entry)

        report = QualityGate.audit_entries(review_entries)

        payload = {
            "metadata": {
                "mod_name": mod_name,
                "exported_at": datetime.now().isoformat(),
                "total_strings": len(review_entries),
                "ready_count": sum(1 for e in review_entries if e.get("translated") and e.get("quality_status") == "ok"),
                "quality_summary": {
                    "is_clean": report.is_clean,
                    "passed": report.passed_count,
                    "leaks": report.leaks_count,
                    "tag_mismatches": report.tag_mismatches_count,
                    "empty": report.empty_count,
                }
            },
            "instructions": "Сэмпай, ты можешь свободно редактировать поле 'translated'. Строки с quality_status='warning' требуют внимания!",
            "entries": review_entries,
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return out_path

    @classmethod
    def load_reviewed_file(cls, filepath: Path) -> List[Dict[str, Any]]:
        """
        Загружает проверенный и отредактированный пользователем файл ревью.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "entries" in data:
            return data["entries"]
        elif isinstance(data, list):
            return data
        return []
