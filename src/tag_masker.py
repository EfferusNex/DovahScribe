import re
from typing import Tuple, Dict, List


class TagMasker:
    """
    Модуль маскирования служебных тегов и плейсхолдеров Скайрима.
    Защищает разметку от повреждения или ошибочного перевода.
    
    Поддерживает:
      - Теги форматирования: <font ...>, </font>, <br>, <p ...>, </p>, <div ...>, </div>
      - Плейсхолдеры движка: <ALIAS=...>, <Alias=...>, <Ref=...>, <Global=...>
      - Разделители страниц: [pagebreak], [PageBreak]
      - Спецификаторы формата: %s, %d, %i, %.1f, %u
    """

    # Регулярные выражения для поиска защищаемых тегов
    PATTERNS = [
        r'<ALIAS=[^>]+>',
        r'<Alias=[^>]+>',
        r'<Ref=[^>]+>',
        r'<Global=[^>]+>',
        r'</?[a-zA-Z][^>]*>',          # Любые HTML-подобные теги (<font...>, </font>, <br>, etc.)
        r'\[[pP]age[bB]reak\]',         # [pagebreak]
        r'%[0-9]*\.?[0-9]*[sdifug]',   # %s, %d, %.1f и т.д.
    ]

    COMBINED_REGEX = re.compile("|".join(f"({p})" for p in PATTERNS), re.IGNORECASE)

    @classmethod
    def mask(cls, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Заменяет все служебные теги в строке на токены [__TAG_0__], [__TAG_1__]...
        Возвращает: (замаскированная_строка, словарь_тегов).
        """
        if not text:
            return text, {}

        tag_map: Dict[str, str] = {}
        tag_counter = 0

        def replace_match(match: re.Match) -> str:
            nonlocal tag_counter
            matched_tag = match.group(0)
            token = f"[__TAG_{tag_counter}__]"
            tag_map[token] = matched_tag
            tag_counter += 1
            return token

        masked_text = cls.COMBINED_REGEX.sub(replace_match, text)
        return masked_text, tag_map

    @classmethod
    def unmask(cls, text: str, tag_map: Dict[str, str]) -> str:
        """
        Восстанавливает оригинальные теги из словаря tag_map в переведенной строке.
        Устойчив к возможным пробелам, добавленным AI (например, [ __TAG_0__ ]).
        """
        if not text or not tag_map:
            return text

        restored_text = text
        for token, original_tag in tag_map.items():
            # Извлекаем номер токена, например '0' из '[__TAG_0__]'
            tag_id_match = re.search(r'\d+', token)
            if tag_id_match:
                tag_id = tag_id_match.group(0)
                # Ищем токен с возможными лишними пробелами: \[ *__TAG_0__ *\]
                flexible_pattern = re.compile(rf'\[\s*__TAG_{tag_id}__\s*\]', re.IGNORECASE)
                restored_text = flexible_pattern.sub(original_tag, restored_text)
            else:
                restored_text = restored_text.replace(token, original_tag)

        return restored_text
