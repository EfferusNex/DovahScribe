"""
Модуль сборки контекстного окна повествования (Narrative Context Buffer).
Группирует строки по логическим сценам, топикам диалогов и страницам книг,
прикрепляя скользящее окно (±2..3 соседние строки), гендерные правила и расовые диалекты.
"""

import json
from typing import List, Dict, Any, Optional


class NarrativeContextBuffer:
    def __init__(self, window_size: int = 2):
        self.window_size = window_size

    def group_items(self, items: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Группирует строки по логическим контекстным блокам:
          - Диалоги (INFO/DIAL): по parent_context.topic_id или formid.
          - Книги (BOOK): по editorid/formid.
          - Квесты (QUST): по editorid/formid.
          - Остальное: по типу записи (ARMO, WEAP и т.д.).
        """
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for item in items:
            r_type = item.get("type", "UNKNOWN")
            parent_ctx = item.get("parent_context", {})
            topic_id = parent_ctx.get("topic_id")

            if topic_id:
                group_key = f"DIAL_TOPIC:{topic_id}"
            elif r_type in ["INFO", "DialogResponses", "DIAL", "DialogTopic"]:
                group_key = f"DIALOG:{item.get('formid', 'misc')}"
            elif r_type in ["BOOK", "Book"]:
                group_key = f"BOOK:{item.get('editorid') or item.get('formid', 'misc')}"
            elif r_type in ["QUST", "Quest"]:
                group_key = f"QUEST:{item.get('editorid') or item.get('formid', 'misc')}"
            else:
                group_key = f"GENERIC:{r_type}"

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)

        return list(groups.values())

    def build_contextual_packages(
        self,
        items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Создает контекстные пакеты для строк, требующих перевода.
        Для каждой целевой строки собирает `context_before` и `context_after`
        из ее группы в пределах `window_size`.
        """
        packages: List[Dict[str, Any]] = []
        groups = self.group_items(items)

        for group in groups:
            for idx, item in enumerate(group):
                # Если строка уже переведена — пропускаем создание пакета для перевода
                if item.get("translated"):
                    continue

                # 1. Собираем контекст ДО (предыдущие 2-3 строки)
                context_before = []
                start_before = max(0, idx - self.window_size)
                for prev_item in group[start_before:idx]:
                    prev_text = prev_item.get("translated") or prev_item.get("text", "")
                    context_before.append({
                        "type": prev_item.get("type"),
                        "path": prev_item.get("path"),
                        "text": prev_text,
                    })

                # 2. Собираем контекст ПОСЛЕ (следующие 2-3 строки)
                context_after = []
                end_after = min(len(group), idx + self.window_size + 1)
                for next_item in group[idx + 1:end_after]:
                    context_after.append({
                        "type": next_item.get("type"),
                        "path": next_item.get("path"),
                        "text": next_item.get("text", ""),
                    })

                # 3. Поиск терминов в едином глобальном глоссарии
                from src.glossary import GlobalGlossary
                matched_glossary = GlobalGlossary().find_matching_terms(item.get("text", ""))

                # 4. Контекст спикера, пола и расового диалекта
                speaker_ctx = item.get("speaker_context", {})

                # 5. Метаданные (родительский топик, вопрос игрока, квест)
                parent_ctx = item.get("parent_context", {})
                package = {
                    "id": item.get("id", len(packages)),
                    "formid": item.get("formid", ""),
                    "type": item.get("type", ""),
                    "path": item.get("path", ""),
                    "target_text": item.get("text", ""),
                    "speaker_context": speaker_ctx,
                    "required_glossary": matched_glossary,
                    "context_before": context_before,
                    "context_after": context_after,
                    "scene_context": {
                        "topic_name": parent_ctx.get("topic_name", ""),
                        "topic_id": parent_ctx.get("topic_id", ""),
                        "editorid": item.get("editorid", ""),
                    },
                }
                packages.append(package)

        return packages

    def format_prompt_for_packages(
        self,
        packages: List[Dict[str, Any]],
        mod_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Форматирует структурированный промпт для AI с полным окружением сцен, расовыми стилями и глоссарием.
        """
        mod_ctx = mod_context or {}
        desc = mod_ctx.get("description", "Мод для The Elder Scrolls V: Skyrim")
        lore = mod_ctx.get("lore", "Лор The Elder Scrolls")

        batch_glossary: Dict[str, str] = {}
        has_female_npc = False
        has_male_npc = False
        has_female_target = False
        dialect_directives: Dict[str, str] = {}

        for pkg in packages:
            batch_glossary.update(pkg.get("required_glossary", {}))
            spk = pkg.get("speaker_context", {})
            role = spk.get("role")
            gender = spk.get("gender")
            tgt_gender = spk.get("target_gender")
            directive = spk.get("style_directive")
            dialect_type = spk.get("dialect_type", "standard")

            if directive and dialect_type != "standard":
                dialect_directives[dialect_type] = directive

            if role == "npc" and gender == "female":
                has_female_npc = True
            elif role == "npc" and gender == "male":
                has_male_npc = True
            if role == "player" and tgt_gender == "female":
                has_female_target = True

        lines = [
            "Ты — ведущий локализатор и эксперт по миру The Elder Scrolls V: Skyrim.",
            f"Концепция мода: {desc}",
            f"Эпоха и лор: {lore}",
            "",
            "ИНСТРУКЦИИ ПО ПЕРЕВОДУ, ГРАММАТИКЕ И СТИЛИСТИКЕ:",
            "1. Переводи целевой текст ('target_text') на выразительный литературный русский язык.",
            "2. Внимательно используй 'speaker_context', 'context_before' и 'context_after':",
        ]

        if has_female_npc:
            lines.append("   • ВНИМАНИЕ (ЖЕНСКИЙ РОД СПИКЕРА): Для реплик NPC женского пола (gender='female') ОБЯЗАТЕЛЬНО используй женский род от первого лица (была, сделала, нашла, пошла, рада, сказала).")
        if has_male_npc:
            lines.append("   • Для реплик NPC мужского пола (gender='male') используй мужской род (был, сделал, нашёл, пошёл, рад).")
        if has_female_target:
            lines.append("   • ВНИМАНИЕ (ОБРАЩЕНИЕ К ЖЕНЩИНЕ): Для вопросов игрока (role='player', target_gender='female') используй женские формы обращения к собеседнице (ты могла бы, будь готова).")

        if dialect_directives:
            lines.append("")
            lines.append("🎭 РАСОВЫЕ ДИАЛЕКТЫ И СТИЛИСТИКА СПИКЕРОВ (СТРОГО СОБЛЮДАЙ!):")
            for d_type, d_text in dialect_directives.items():
                lines.append(f"   • {d_text}")

        lines.extend([
            "",
            "   • Учитывай эмоциональный тон (страх, сарказм, приказ, мольба, игривость).",
            "   • Поддерживай связность диалоговой ветки.",
            "3. Сохраняй нетронутыми игровые теги: <font color='...'>, <br>, <ALIAS=...>, %s, [pagebreak].",
        ])

        if batch_glossary:
            lines.append("4. ОБЯЗАТЕЛЬНЫЙ ГЛОССАРИЙ (строго используй эти переводы терминов):")
            for en, ru in sorted(batch_glossary.items()):
                lines.append(f"   • \"{en}\" -> строго переводить как \"{ru}\"")
            lines.append("5. Ответ верни строго в виде JSON-списка: [{\"id\": ..., \"translated\": \"...\"}].")
        else:
            lines.append("4. Ответ верни строго в виде JSON-списка: [{\"id\": ..., \"translated\": \"...\"}].")

        lines.append("")
        lines.append("ПАКЕТЫ СТРОК ДЛЯ ПЕРЕВОДА:")
        lines.append(json.dumps(packages, ensure_ascii=False, indent=2))
        return "\n".join(lines)
