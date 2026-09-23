"""
🐾 Quality Gate & Language Leak Detector (Контроль качества локализации).
Проверяет строки перевода на:
  1. Утечки английского/латинского текста в переведенных полях (Language Leaks).
  2. Сохранность служебных тегов (<font>, <ALIAS=...>, %s, %d, [pagebreak]).
  3. Корректность и полноту заполнения.
  4. Пропуск технических системных идентификаторов ($MCM, pRing*, vFaction, римские цифры).
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, field


@dataclass
class QualityIssue:
    item_id: Any
    formid: str
    field: str
    original: str
    translated: str
    issue_type: str  # 'language_leak', 'tag_mismatch', 'empty_translation', 'untranslated'
    details: str


@dataclass
class QualityReport:
    total_checked: int = 0
    passed_count: int = 0
    issues_count: int = 0
    leaks_count: int = 0
    tag_mismatches_count: int = 0
    empty_count: int = 0
    glossary_mismatches_count: int = 0
    issues: List[QualityIssue] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return self.issues_count == 0

    def summary(self) -> str:
        status_symbol = "✅" if self.is_clean else "⚠️"
        return (
            f"{status_symbol} Quality Report: Всего {self.total_checked} | "
            f"Чисто: {self.passed_count} | "
            f"Проблем: {self.issues_count} "
            f"(Утечек: {self.leaks_count}, Теги: {self.tag_mismatches_count}, Пусто: {self.empty_count}, Глоссарий: {self.glossary_mismatches_count})"
        )


class QualityGate:
    """
    Детектор языковых утечек и валидатор качества локализации Skyrim.
    """

    # Допустимые аббревиатуры и термины латиницей, которые не считаются ошибкой
    WHITELIST_WORDS: Set[str] = {
        "DPS", "FPS", "ID", "HP", "MP", "HUD", "MCM", "UI", "3D", "2D",
        "FO4", "TES", "SKSE", "F4SE", "SSE", "VR", "XP", "SP",
        "DLL", "SWF", "LOTD", "JSON", "IE", "EE", "SE", "AE", "BOM", "INI",
        "PEX", "PSC", "NIF", "DDS", "BSA", "SKSE64", "SKYUI", "PAPYRUSUTIL", "PAPYRUS",
        "DATA", "PLUGINS", "INTERFACE", "TRANSLATIONS", "SCRIPTS", "MESHES", "TEXTURES", "SOUND", "MUSIC", "STRINGS",
        "DEFAULTCONFIG", "QUICKLOOT", "QUICKLOOTIE", "ATOMCRAFTY", "COMPLETIONIST",
        "NPC", "DEFEAT", "ZAZ", "NSAP", "UIEXTENSIONS", "PARADISE", "HALLS", "ANIMATION",
        "E", "R", "F", "C", "Z", "X", "V", "Q", "W", "A", "S", "D", "M1", "M2", "TAB", "SHIFT", "ALT", "CTRL"
    }

    # Римские цифры (I, II, III, IV, V, VI, VII, VIII, IX, X, XI, XII, XIII, XIV, XV, XVI, XVII, XVIII, XIX, XX)
    ROMAN_NUMERALS_PATTERN = re.compile(
        r"\b(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})\b",
        re.IGNORECASE
    )

    # Системные переменные, скриптовые префиксы и токены ($TOKEN, pRing*, vFaction, xxp, CF_*, aaa_*, etc.)
    SYSTEM_TOKEN_PATTERN = re.compile(
        r"^\$[A-Za-z0-9_]+$|^(p|v|xxp|f|k|q|z|aaa|CF|vk)[A-Za-z0-9_]*$|^[A-Za-z0-9_]+(Script|Quest|Spell|Faction|Effect|Ability|Armor|Weapon)$",
        re.IGNORECASE
    )

    # Теги и подстановки Skyrim
    TAG_PATTERNS = [
        re.compile(r"<font[^>]*>", re.IGNORECASE),
        re.compile(r"</font>", re.IGNORECASE),
        re.compile(r"<alias=[^>]+>", re.IGNORECASE),
        re.compile(r"<[^>]+>", re.IGNORECASE),
        re.compile(r"\[pagebreak\]", re.IGNORECASE),
        re.compile(r"%[0-9\.\-+]*[sdfgixX%]"),
        re.compile(r"\\r|\\n|\\t"),
        re.compile(r"&[a-zA-Z]+;"),
        re.compile(r"#?[0-9A-Fa-f]{6}"),  # HEX цвета типа #FFFFFF или FFFF00
        re.compile(r"\b[0-9]+[a-zA-Z]+\b|\b[a-zA-Z]+[0-9]+\b"),  # Ники/авторские теги вида 5chars, 3d, mod4
    ]

    # Поиск латинских слов из 2 и более букв
    # Поиск латинских слов из 2 и более букв
    LATIN_WORD_PATTERN = re.compile(r"[a-zA-Z]{2,}")

    @classmethod
    def sanitize_false_friends(cls, original: str, translated: str) -> str:
        """
        Автоматически исправляет грубые машинные ляпы перевода через динамический FalseFriendsEngine.
        """
        try:
            from src.false_friends import FalseFriendsEngine
            return FalseFriendsEngine().sanitize_text(original, translated)
        except Exception:
            return translated

    @classmethod
    def detect_false_friends(cls, original: str, translated: str) -> List[Dict[str, Any]]:
        """
        Обнаруживает вхождения ложных друзей через динамический FalseFriendsEngine.
        """
        try:
            from src.false_friends import FalseFriendsEngine
            return FalseFriendsEngine().detect_issues(original, translated)
        except Exception:
            return []

    @classmethod
    def strip_safe_tokens(cls, text: str) -> str:
        """
        Удаляет из строки валидные теги, hex-коды, служебные разметки и римские цифры.
        Оставляет только значимый текст для проверки на утечку латиницы.
        """
        cleaned = text

        # 1. Удаляем теги и подстановки
        for pattern in cls.TAG_PATTERNS:
            cleaned = pattern.sub(" ", cleaned)

        # 2. Удаляем цепочки путей папок и файлов (Data > SKSE > Plugins > QuicklootIE > DefaultConfig.json)
        cleaned = re.sub(r"(?:[A-Za-z0-9_\-]+\s*(?:>|/|\\)\s*)+[A-Za-z0-9_\-\.]+", " ", cleaned)

        # 3. Удаляем системные токены $NAME и имена файлов (например DefaultConfig.json)
        cleaned = re.sub(r"\$[A-Za-z0-9_]+", " ", cleaned)
        cleaned = re.sub(r"\b[A-Za-z0-9_\-]+\.(json|ini|txt|pex|psc|dll|swf|nif|dds|bsa|esp|esm|esl|xml|log|toml|yaml)\b", " ", cleaned, flags=re.IGNORECASE)

        # 4. Удаляем римские цифры
        cleaned = cls.ROMAN_NUMERALS_PATTERN.sub(" ", cleaned)

        return cleaned

    @classmethod
    def detect_language_leak(cls, text: str, original: str = "") -> Tuple[bool, List[str]]:
        """
        Проверяет строку перевода на наличие непереведенных английских слов.
        
        Возвращает:
          (has_leak, list_of_leaked_words)
        """
        if not text or not text.strip():
            return False, []

        cleaned = cls.strip_safe_tokens(text)
        words = cls.LATIN_WORD_PATTERN.findall(cleaned)

        leaked_words = []
        for word in words:
            upper_word = word.upper()
            if upper_word in cls.WHITELIST_WORDS:
                continue
            # Если это системный токен (например скриптовая переменная, которая была в оригинале)
            if cls.SYSTEM_TOKEN_PATTERN.match(word) and word in original:
                continue
            # Если это параметр/литерал в кавычках в оригинале ('value', "weight", `param`)
            if (f"'{word}'" in original or f'"{word}"' in original or f"`{word}`" in original or
                f"'{word.lower()}'" in original.lower() or f'"{word.lower()}"' in original.lower()):
                continue
            leaked_words.append(word)

        has_leak = len(leaked_words) > 0
        return has_leak, leaked_words

    @classmethod
    def check_tag_parity(cls, original: str, translated: str) -> Tuple[bool, str]:
        """
        Проверяет соответствие ключевых тегов (ALIAS, %s, font) между оригиналом и переводом.
        """
        # Проверка alias тегов
        orig_aliases = set(re.findall(r"<alias=[^>]+>", original, re.IGNORECASE))
        trans_aliases = set(re.findall(r"<alias=[^>]+>", translated, re.IGNORECASE))
        if orig_aliases != trans_aliases:
            return False, f"Несовпадение тегов ALIAS: в оригинале {orig_aliases}, в переводе {trans_aliases}"

        # Проверка формата %s, %d
        orig_specifiers = re.findall(r"%[0-9\.\-+]*[sdfgixX]", original)
        trans_specifiers = re.findall(r"%[0-9\.\-+]*[sdfgixX]", translated)
        if sorted(orig_specifiers) != sorted(trans_specifiers):
            return False, f"Несовпадение спецификаторов формата: {orig_specifiers} vs {trans_specifiers}"

        return True, ""

    @classmethod
    def _extract_russian_stem(cls, word: str) -> str:
        """
        Упрощенный стемминг русского слова (отсечение флексий/окончаний)
        для гибкой сверки терминов с учетом падежей и родов.
        """
        clean = re.sub(r"[^\w\s]", "", word, flags=re.UNICODE).strip().lower()
        if len(clean) <= 3:
            return clean
        # Отсекаем типовые окончания прилагательных и существительных
        for suffix in [
            "ского", "скому", "скими", "ском", "ской", "ских", "ская", "ское", "ские", "ский",
            "ного", "ному", "ными", "ном", "ной", "ных", "ная", "ное", "ные", "ный",
            "ение", "ения", "ению", "ением", "ении",
            "ого", "его", "ому", "ему", "ыми", "ими", "ами", "ями", "ах", "ях",
            "ой", "ей", "ем", "ом", "ам", "ям", "ов", "ев",
            "а", "я", "о", "е", "ы", "и", "у", "ю", "ь"
        ]:
            if clean.endswith(suffix) and len(clean) - len(suffix) >= 3:
                return clean[:-len(suffix)]
        return clean

    @classmethod
    def check_glossary_consistency(
        cls,
        original: str,
        translated: str,
        glossary_matches: Optional[Dict[str, str]] = None
    ) -> List[Tuple[str, str]]:
        """
        Проверяет, переведены ли термины глоссария в соответствии с каноном.
        Возвращает список кортежей нарушений [(en_term, expected_ru_term), ...]
        """
        if not original or not translated:
            return []

        if glossary_matches is None:
            try:
                from src.glossary import GlobalGlossary
                glossary_matches = GlobalGlossary().find_matching_terms(original)
            except Exception:
                return []

        if not glossary_matches:
            return []

        mismatches = []
        trans_lower = translated.lower()

        for en_term, expected_ru in glossary_matches.items():
            # 1. Прямой поиск перевода (без учета регистра)
            if expected_ru.lower() in trans_lower:
                continue

            # 2. Пословный поиск стеммов для составных и склоняемых терминов
            ru_words = expected_ru.split()
            all_stems_found = True
            for w in ru_words:
                stem = cls._extract_russian_stem(w)
                if len(stem) >= 3 and stem not in trans_lower:
                    all_stems_found = False
                    break

            if not all_stems_found:
                mismatches.append((en_term, expected_ru))

        return mismatches

    @classmethod
    def validate_entry(cls, entry: Dict[str, Any], check_glossary: bool = True) -> Optional[QualityIssue]:
        """
        Проверяет одну запись на все виды нарушений качества.
        """
        item_id = entry.get("id", "")
        formid = entry.get("formid", "")
        field_name = entry.get("field") or entry.get("path") or ""
        original = entry.get("original") or entry.get("text") or ""
        translated = entry.get("translated", "")
        source = entry.get("source", "")
        # 0. Если пользователь явно выбрал оставить оригинал без перевода
        if source == "keep_original":
            return None

        # 1. Если перевод пустой
        if not translated or not str(translated).strip():
            if original.strip():
                return QualityIssue(
                    item_id=item_id,
                    formid=formid,
                    field=field_name,
                    original=original,
                    translated="",
                    issue_type="empty_translation",
                    details="Перевод отсутствует или пуст"
                )
        # 2. Если значение является системным токеном или скриптовым идентификатором
        if cls.SYSTEM_TOKEN_PATTERN.match(original.strip()):
            return None

        # 3. Если перевод полностью совпадает с английским оригиналом (не переведено)
        if translated.strip() == original.strip():
            has_leak, leaked = cls.detect_language_leak(translated, original)
            if has_leak:
                return QualityIssue(
                    item_id=item_id,
                    formid=formid,
                    field=field_name,
                    original=original,
                    translated=translated,
                    issue_type="untranslated",
                    details=f"Строка оставлена без перевода (английский): {', '.join(leaked[:5])}"
                )

        # 4. Проверка на утечку латиницы (частичный перевод / непереведенные слова)
        has_leak, leaked = cls.detect_language_leak(translated, original)
        if has_leak:
            return QualityIssue(
                item_id=item_id,
                formid=formid,
                field=field_name,
                original=original,
                translated=translated,
                issue_type="language_leak",
                details=f"Обнаружены непереведенные английские слова: {', '.join(leaked[:5])}"
            )

        # 5. Проверка целостности тегов
        tags_ok, tag_err = cls.check_tag_parity(original, translated)
        if not tags_ok:
            return QualityIssue(
                item_id=item_id,
                formid=formid,
                field=field_name,
                original=original,
                translated=translated,
                issue_type="tag_mismatch",
                details=tag_err
            )

        # 6. Проверка на ложных друзей переводчика и грубые машинные ошибки
        ff_issues = cls.detect_false_friends(original, translated)
        if ff_issues:
            first_ff = ff_issues[0]
            return QualityIssue(
                item_id=item_id,
                formid=formid,
                field=field_name,
                original=original,
                translated=translated,
                issue_type="false_friend",
                details=f"{first_ff['description']} (Рекомендуется замена на '{first_ff['expected']}')"
            )

        # 7. Проверка соответствия терминов единому глобальному глоссарию
        if check_glossary and original and translated:
            glossary_errors = cls.check_glossary_consistency(original, translated)
            if glossary_errors:
                details_list = [f"'{en}' -> '{ru}'" for en, ru in glossary_errors]
                return QualityIssue(
                    item_id=item_id,
                    formid=formid,
                    field=field_name,
                    original=original,
                    translated=translated,
                    issue_type="glossary_mismatch",
                    details=f"Несоблюдение глоссария: {', '.join(details_list)}"
                )

        return None

    @classmethod
    def audit_entries(cls, entries: List[Dict[str, Any]], check_glossary: bool = True) -> QualityReport:
        """
        Проводит полный аудит списка записей и возвращает сводный отчет.
        """
        report = QualityReport(total_checked=len(entries))

        for entry in entries:
            issue = cls.validate_entry(entry, check_glossary=check_glossary)
            if issue:
                report.issues.append(issue)
                report.issues_count += 1
                if issue.issue_type in ["language_leak", "untranslated"]:
                    report.leaks_count += 1
                elif issue.issue_type == "tag_mismatch":
                    report.tag_mismatches_count += 1
                elif issue.issue_type == "empty_translation":
                    report.empty_count += 1
                elif issue.issue_type == "glossary_mismatch":
                    report.glossary_mismatches_count += 1
            else:
                report.passed_count += 1

        return report
