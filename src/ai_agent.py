"""
🐾 Модуль агентного перевода Леин (AI Translation Coordinator).
Реализует:
  - Формирование интеллектуальных стеков (чанков) для диалогов, книг и предметов.
  - Автоматическое маскирование/размаскирование служебных тегов через TagMasker.
  - Экспорт результатов в промежуточный файл ревью для проверки Сэмпаем (ReviewManager).
  - Валидацию целостности (проверка вернувшихся ID, выявление пропущенных строк).
  - Детекцию утечек английского и битых тегов через QualityGate (автоматический сбор пакетов на retry).
"""

import json
from typing import List, Dict, Any, Tuple, Optional
from src.tag_masker import TagMasker
from src.narrative_context import NarrativeContextBuffer
from src.review_manager import ReviewManager
from src.quality_gate import QualityGate, QualityIssue


class AIAgentCoordinator:
    def __init__(
        self,
        dialog_batch_size: int = 20,
        generic_batch_size: int = 35,
        book_batch_size: int = 5,
    ):
        self.dialog_batch_size = dialog_batch_size
        self.generic_batch_size = generic_batch_size
        self.book_batch_size = book_batch_size
        self.context_buffer = NarrativeContextBuffer(window_size=2)

    def split_into_chunks(self, items: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Разбивает список элементов на интеллектуальные стеки:
          - Диалоги группируются по топикам/сценам до ~20 реплик на пачку;
          - Книги: до 5 страниц/записей;
          - Предметы: до 35 элементов.
        """
        groups = self.context_buffer.group_items(items)
        chunks: List[List[Dict[str, Any]]] = []

        current_chunk: List[Dict[str, Any]] = []
        current_chunk_type = ""

        for group in groups:
            if not group:
                continue

            first_item = group[0]
            r_type = first_item.get("type", "UNKNOWN")
            is_dialog = r_type in ["INFO", "DialogResponses", "DIAL", "DialogTopic"]
            is_book = r_type in ["BOOK", "Book"]

            max_size = (
                self.dialog_batch_size if is_dialog else (
                    self.book_batch_size if is_book else self.generic_batch_size
                )
            )

            # Если добавление группы превысит размер чанка или изменился базовый тип (диалог vs предмет)
            chunk_category = "dialog" if is_dialog else ("book" if is_book else "item")
            if current_chunk and (
                len(current_chunk) + len(group) > max_size or current_chunk_type != chunk_category
            ):
                chunks.append(current_chunk)
                current_chunk = []

            current_chunk_type = chunk_category
            current_chunk.extend(group)

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def prepare_batch_payload(
        self,
        chunk: List[Dict[str, Any]],
        mod_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[int, Dict[str, str]]]:
        """
        Подготавливает пачку строк для передачи в AI:
          1. Применяет маскирование тегов к каждому target_text.
          2. Собирает контекстные пакеты со скользящим окном.
          3. Формирует структурированный промпт.
        
        Возвращает:
          (prompt_text, tag_maps_by_id)
        """
        packages = self.context_buffer.build_contextual_packages(chunk)
        tag_maps: Dict[int, Dict[str, str]] = {}

        # Маскируем теги в каждом целевом тексте
        for pkg in packages:
            pkg_id = pkg["id"]
            raw_target = pkg["target_text"]
            masked_target, tag_map = TagMasker.mask(raw_target)
            pkg["target_text"] = masked_target
            if tag_map:
                tag_maps[pkg_id] = tag_map

        prompt_str = self.context_buffer.format_prompt_for_packages(packages, mod_context)
        return prompt_str, tag_maps

    def apply_translations_and_unmask(
        self,
        chunk: List[Dict[str, Any]],
        ai_responses: List[Dict[str, Any]],
        tag_maps: Dict[int, Dict[str, str]],
        strict_quality_check: bool = True,
    ) -> Tuple[List[Dict[str, Any]], List[int]]:
        """
        Применяет полученные переводы, размаскирует теги и проверяет целостность.
        Если strict_quality_check=True, выявляет строки с языковыми утечками (непереведенный английский)
        или несовпадающими тегами и возвращает их в retry_ids.
        
        Возвращает:
          (обновленный_список_элементов, список_пропущенных_или_дефектных_id_для_retry)
        """
        resp_by_id = {r["id"]: r.get("translated", "") for r in ai_responses if "id" in r}
        retry_ids = []

        for item in chunk:
            item_id = item.get("id")
            if item_id in resp_by_id:
                raw_translation = resp_by_id[item_id]
                # Восстанавливаем защищенные теги
                if item_id in tag_maps:
                    final_translation = TagMasker.unmask(raw_translation, tag_maps[item_id])
                else:
                    final_translation = raw_translation

                item["translated"] = final_translation
                item["source"] = "lain_agent"

                if strict_quality_check:
                    issue = QualityGate.validate_entry(item)
                    if issue:
                        item["quality_issue"] = issue.details
                        retry_ids.append(item_id)
            else:
                retry_ids.append(item_id)

        return chunk, retry_ids
