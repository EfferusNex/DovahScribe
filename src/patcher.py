import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from src.quality_gate import QualityGate, QualityReport

BASE_DIR = Path(__file__).resolve().parent.parent
PATCHES_DIR = BASE_DIR / "data" / "patches"
PATCHES_DIR.mkdir(parents=True, exist_ok=True)


class Patcher:
    """
    Модуль сборки патча перевода через houseCARL.
    Преобразует переведенные записи в массив операций (ops) для вызова housecarl_apply
    с обязательной предварительной проверкой через QualityGate.
    """

    @classmethod
    def build_patch_ops(
        cls,
        translated_items: List[Dict[str, Any]],
        validate_quality: bool = True,
        allow_leaks: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Optional[QualityReport]]:
        """
        Формирует список операций (ops) для housecarl_apply.
        Принимает как элементы из review-файла (с ключами 'field', 'translated'),
        так и внутренние структуры (с ключами 'path', 'translated').
        
        Если validate_quality=True, строки проверяются на утечки английского и битые теги.
        Если allow_leaks=False, проблемные строки отсеиваются от попадания в патч.
        """
        report: Optional[QualityReport] = None
        if validate_quality:
            report = QualityGate.audit_entries(translated_items)

        ops: List[Dict[str, Any]] = []

        for item in translated_items:
            translated_val = item.get("translated")
            formid = item.get("formid")
            field_path = item.get("field") or item.get("path")

            if not formid or not field_path:
                continue

            # Добавляем в патч только те строки, у которых есть непустой перевод
            if not translated_val or not isinstance(translated_val, str) or not translated_val.strip():
                continue

            # Если включена строгая валидация качества и утечки запрещены
            if validate_quality and not allow_leaks:
                issue = QualityGate.validate_entry(item)
                if issue:
                    # Пропускаем строку с дефектом перевода
                    continue

            ops.append({
                "formid": formid,
                "field_path": field_path,
                "value": translated_val.strip(),
                "op": "Set"
            })

        return ops, report

    @classmethod
    def save_ops_manifest(cls, mod_name: str, ops: List[Dict[str, Any]]) -> Path:
        """Сохраняет массив операций в JSON-манифест для передачи в housecarl_apply."""
        clean_name = mod_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        manifest_path = PATCHES_DIR / f"{clean_name}_ops.json"
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(ops, f, ensure_ascii=False, indent=2)

        return manifest_path

    @classmethod
    def prepare_apply_params(
        cls,
        mod_name: str,
        ops: List[Dict[str, Any]],
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Формирует словарь параметров для вызова MCP инструмента housecarl_apply.
        """
        clean_name = mod_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        patch_name = f"TranslationPatch_{clean_name}"

        return {
            "patch": patch_name,
            "ops": ops,
            "dry_run": dry_run,
            "format": "json"
        }
