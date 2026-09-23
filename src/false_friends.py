"""
🐾 Dynamic Anti-False-Friends Engine (Реестр ложных друзей переводчика и машинных ляпов).
Управляет базой типовых ошибок (data/false_friends.json) с поддержкой:
  1. Динамической загрузки и горячего обновления без правок кода.
  2. Автоматического распознавания стеммов и окончаний (гонк* ➔ рас*).
  3. Пакетной санитизации текстов при импорте и экспорте.
  4. Добавления новых правил на лету через API или CAT-дашборд.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FALSE_FRIENDS_FILE = DATA_DIR / "false_friends.json"


class FalseFriendsEngine:
    """Движок динамического реестра ложных друзей переводчика TES."""

    _instance: Optional['FalseFriendsEngine'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FalseFriendsEngine, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        self.filepath = FALSE_FRIENDS_FILE
        self.rules: List[Dict[str, Any]] = []
        self.compiled_rules: List[Dict[str, Any]] = []
        self.load_rules()

    def load_rules(self):
        """Загружает правила из JSON-файла и компилирует регулярные выражения."""
        if not self.filepath.exists():
            self.rules = []
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
        except Exception as e:
            print(f"⚠️ Ошибка загрузки false_friends.json: {e}")
            self.rules = []

        self._compile_rules()

    def save_rules(self):
        """Сохраняет текущие правила в JSON-файл."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
            self._compile_rules()
        except Exception as e:
            print(f"⚠️ Ошибка сохранения false_friends.json: {e}")

    def _compile_rules(self):
        """Компилирует паттерны для сверхбыстрого матчинга в пайплайне."""
        self.compiled_rules = []
        for r in self.rules:
            triggers = r.get("trigger_en", [])
            if isinstance(triggers, str):
                triggers = [triggers]

            # Регулярка для английских триггеров
            en_pattern_str = r"\b(?:" + "|".join([re.escape(t) for t in triggers]) + r")[s]?\b"
            en_regex = re.compile(en_pattern_str, re.IGNORECASE)

            bad_ru = r.get("bad_ru", [])
            if isinstance(bad_ru, str):
                bad_ru = [bad_ru]

            # Преобразуем маски вида "гонк*" в регулярные выражения
            ru_patterns = []
            for b in bad_ru:
                if b.endswith("*"):
                    stem = re.escape(b[:-1])
                    ru_patterns.append(rf"\b{stem}[а-яёА-ЯЁ]*\b")
                else:
                    ru_patterns.append(rf"\b{re.escape(b)}\b")

            ru_regex = re.compile(r"|".join(ru_patterns), re.IGNORECASE) if ru_patterns else None

            self.compiled_rules.append({
                "id": r.get("id", ""),
                "en_regex": en_regex,
                "ru_regex": ru_regex,
                "forms": r.get("forms", {}),
                "correct_ru": r.get("correct_ru", ""),
                "description": r.get("description", ""),
                "category": r.get("category", "General"),
                "raw_rule": r
            })

    def add_rule(
        self,
        trigger_en: List[str] | str,
        bad_ru: List[str] | str,
        correct_ru: str,
        description: str = "",
        category: str = "User",
        forms: Optional[Dict[str, str]] = None
    ) -> bool:
        """Добавляет новое правило в реестр и автоматически сохраняет его."""
        t_en = [trigger_en] if isinstance(trigger_en, str) else trigger_en
        b_ru = [bad_ru] if isinstance(bad_ru, str) else bad_ru

        rule_id = f"rule_{len(self.rules) + 1}_{t_en[0].lower()}"

        new_rule = {
            "id": rule_id,
            "trigger_en": t_en,
            "bad_ru": b_ru,
            "correct_ru": correct_ru,
            "description": description or f"Замена '{b_ru[0]}' -> '{correct_ru}' при триггере '{t_en[0]}'",
            "category": category,
            "forms": forms or {}
        }

        self.rules.append(new_rule)
        self.save_rules()
        return True

    def sanitize_text(self, original: str, translated: str) -> str:
        """
        Проводит автоматическую очистку текста от ложных друзей и машинных ляпов.
        """
        if not original or not translated:
            return translated

        res = translated
        for cr in self.compiled_rules:
            # 1. Проверяем, есть ли английский триггер в оригинале
            if cr["en_regex"] and cr["en_regex"].search(original):
                # 2. Если есть готовый словарь форм (падежей)
                if cr["forms"]:
                    for bad_word, good_word in cr["forms"].items():
                        # Точная замена границ слова
                        pattern = rf"\b{re.escape(bad_word)}\b"
                        res = re.sub(pattern, good_word, res)

                # 3. Если есть маска со звёздочкой (например гонк* -> рас*)
                elif cr.get("correct_ru") and cr.get("correct_ru").endswith("*"):
                    correct_stem = cr["correct_ru"][:-1]
                    bad_stem = cr["raw_rule"].get("bad_ru", "")
                    if isinstance(bad_stem, list) and bad_stem:
                        bad_stem = bad_stem[0]
                    if isinstance(bad_stem, str) and bad_stem.endswith("*"):
                        b_stem = bad_stem[:-1]
                        # Заменяем основу с сохранением окончаний
                        def replacer(match):
                            word = match.group(0)
                            suffix = word[len(b_stem):]
                            if word[0].isupper():
                                return correct_stem.capitalize() + suffix
                            return correct_stem.lower() + suffix

                        res = re.sub(rf"\b{re.escape(b_stem)}([а-яёА-ЯЁ]*)\b", replacer, res, flags=re.IGNORECASE)

        return res

    def detect_issues(self, original: str, translated: str) -> List[Dict[str, Any]]:
        """
        Обнаруживает вхождения ложных друзей и возвращает список замечаний для Quality Gate.
        """
        if not original or not translated:
            return []

        issues = []
        for cr in self.compiled_rules:
            if cr["en_regex"] and cr["en_regex"].search(original):
                if cr["ru_regex"] and cr["ru_regex"].search(translated):
                    issues.append({
                        "id": cr["id"],
                        "description": cr["description"],
                        "expected": cr["correct_ru"],
                        "category": cr["category"]
                    })
        return issues
