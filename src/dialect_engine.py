"""
🐾 Race & Lore Dialect Engine (Стилистический движок рас и лорных диалектов TES).
Определяет:
  1. Расовую принадлежность и диалект NPC (каноничные расы, субрасы и кастомные расы из модов).
  2. 4-уровневую детекцию: VoiceType (VTYP) -> Keywords (KWDA) -> Семантика субрас -> Safe Fallback.
  3. Стилистические инструкции для LLM (речь каджитов от 3-го лица, хладнокровие аргониан, властность даэдра).
"""

import re
from typing import Dict, Any, List, Optional, Tuple


class DialectProfile:
    """Профиль диалекта расы с инструкциями для ИИ."""

    def __init__(
        self,
        dialect_id: str,
        display_name: str,
        emoji: str,
        system_directive: str,
        key_phrases: List[str],
    ):
        self.dialect_id = dialect_id
        self.display_name = display_name
        self.emoji = emoji
        self.system_directive = system_directive
        self.key_phrases = key_phrases

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dialect_id": self.dialect_id,
            "display_name": self.display_name,
            "emoji": self.emoji,
            "system_directive": self.system_directive,
            "key_phrases": self.key_phrases,
        }


# База каноничных стилистических профилей TES
DIALECT_PROFILES: Dict[str, DialectProfile] = {
    "khajiit": DialectProfile(
        dialect_id="khajiit",
        display_name="Каджит",
        emoji="🐾",
        system_directive=(
            "СПИКЕР — КАДЖИТ (Khajiit). "
            "ПРАВИЛА РЕЧИ: "
            "1. Говорить о себе ИСКЛЮЧИТЕЛЬНО в третьем лице («этот каджит», «каджит», «мы» или по имени персонажа). "
            "СТРОГО ИЗБЕГАТЬ местоимений первого лица «я», «мой», «мне»! (Вместо «Я знаю» -> «Этот каджит знает» / «Дж'зарго знает»). "
            "2. Мягкий, вкрадчивый, слегка лукавый тон. Характерные метафоры про пески, теплые ветры, луны (Массер и Секунда), сахар."
        ),
        key_phrases=["этот каджит", "теплые пески", "каджит знает", "лунный сахар"],
    ),
    "argonian": DialectProfile(
        dialect_id="argonian",
        display_name="Аргонианин",
        emoji="🦎",
        system_directive=(
            "СПИКЕР — АРГОНИАНИН / САКСХЛИЛ (Argonian / Saxhleel). "
            "ПРАВИЛА РЕЧИ: "
            "1. Спокойный, хладнокровный, взвешенный тон без лишней экзальтации. "
            "2. Аллегории и метафоры, связанные с водой, болотами, корнями, Хистом, плавниками («мои плавники спокойны», «течения ведут нас», «пусть твоя чешуя остается влажной»). "
            "3. Прямота и отсутствие пустой лести."
        ),
        key_phrases=["плавники", "корни Хиста", "болота", "течения"],
    ),
    "daedric": DialectProfile(
        dialect_id="daedric",
        display_name="Даэдра / Дремора",
        emoji="👑",
        system_directive=(
            "СПИКЕР — ДАЭДРА / ДРЕМОРА / ПРИНЦ ДАЭДРА. "
            "ПРАВИЛА РЕЧИ: "
            "1. Властный, надменный, архаичный и грозный слог. "
            "2. Обращение к собеседнику с позиции превосходства («смертный», «червь», «ничтожество», «пешка»). "
            "3. Торжественные, тяжелые конструкции без суеты и просторечия."
        ),
        key_phrases=["смертный", "Обливион", "ничтожество", "воля"],
    ),
    "orc": DialectProfile(
        dialect_id="orc",
        display_name="Орк (Орсимер)",
        emoji="⚔️",
        system_directive=(
            "СПИКЕР — ОРК / ОРСИМЕР (Orc / Orsimer). "
            "ПРАВИЛА РЕЧИ: "
            "1. Прямой, лаконичный, суровый и честный воинский тон. "
            "2. Уважение к силе, кузнечному делу, Кодексу Малаката и чести воина. "
            "3. Без витиеватых придворных оборотов."
        ),
        key_phrases=["Малакат", "честь воина", "крепость", "сталь"],
    ),
    "dunmer": DialectProfile(
        dialect_id="dunmer",
        display_name="Данмер (Тёмный эльф)",
        emoji="🏛️",
        system_directive=(
            "СПИКЕР — ДАНМЕР / ТЕМНЫЙ ЭЛЬФ (Dunmer / Dark Elf). "
            "ПРАВИЛА РЕЧИ: "
            "1. Сдержанный скепсис, скрытность, уважение к традициям Предков. "
            "2. Возможны специфические лорные восклицания и обращения (н'вах, сера, мутсэра), если это уместно по контексту."
        ),
        key_phrases=["чужеземец", "н'вах", "сера", "предки"],
    ),
    "nord": DialectProfile(
        dialect_id="nord",
        display_name="Норд",
        emoji="❄️",
        system_directive=(
            "СПИКЕР — НОРД (Nord). "
            "ПРАВИЛА РЕЧИ: "
            "1. Прямодушный, суровый, колоритный северный слог. "
            "2. Упоминания Совнгарда, чести, холода, браги, предков Скайрима."
        ),
        key_phrases=["Совнгард", "во имя Тороса", "во славу", "брага"],
    ),
}


class DialectClassifier:
    """
    Классификатор рас и лорных диалектов с поддержкой кастомных рас модов.
    """

    # Ванильные FormID рас в Skyrim.esm / Update.esm / Dawnguard / Dragonborn
    VANILLA_RACE_FORMIDS: Dict[str, str] = {
        # Khajiit
        "00013745": "khajiit",  # KhajiitRace
        "00088845": "khajiit",  # KhajiitRaceVampire
        "00013741": "khajiit",  # KhajiitRaceChild / Alt
        # Argonian
        "00013740": "argonian", # ArgonianRace
        "0008883a": "argonian", # ArgonianRaceVampire
        "00013742": "argonian", # ArgonianRaceChild / Alt
        # Dremora / Daedra
        "00013748": "daedric",  # DremoraRace
        "00097a3d": "daedric",  # AtronachFlame
        "00097a3e": "daedric",  # AtronachFrost
        "00097a3f": "daedric",  # AtronachStorm
        # Orc
        "00013747": "orc",      # OrcRace
        "00088846": "orc",      # OrcRaceVampire
        # Dunmer
        "00013743": "dunmer",   # DarkElfRace
        "0008883d": "dunmer",   # DarkElfRaceVampire
        # Nord
        "00013746": "nord",     # NordRace
        "00088842": "nord",     # NordRaceVampire
    }

    # Семантические паттерны субрас и кастомных рас
    SUBRACE_PATTERNS = [
        # Каджиты и их субрасы (включая моды: Ohmes, Dagi, Alfiq, Cathay, Suthay, Pahmar)
        (r'(khajiit|ohmes|dagi|alfiq|cathay|suthay|pahmar|tojay|feline|catfolk|bastet|neko)', 'khajiit'),
        # Аргониане и саксхлил (включая моды: Saxhleel, Naga, Agaceph, Paatru, Sarpa, Lilmothiit, Lizard)
        (r'(argonian|saxhleel|naga|agaceph|paatru|sarpa|lizardfolk|reptilian)', 'argonian'),
        # Дремора, Даэдра, Демоны
        (r'(dremora|daedra|daedric|scamp|auroran|seducer|golden saint|xivilai|hermaeus|sheogorath|molag|mehrunes)', 'daedric'),
        # Орки
        (r'(orc|orsimer|ironorc|woodorc)', 'orc'),
        # Данмеры / Тёмные эльфы
        (r'(darkelf|dunmer|chimer|ashlander)', 'dunmer'),
        # Норды
        (r'(nord|atmoran|skaal)', 'nord'),
    ]

    # Паттерны для типов голосов (Voice Types / VTYP)
    VOICE_PATTERNS = [
        (r'khajiit', 'khajiit'),
        (r'argonian', 'argonian'),
        (r'dremora', 'daedric'),
        (r'daedric', 'daedric'),
        (r'orc', 'orc'),
        (r'darkelf|dunmer', 'dunmer'),
        (r'nord', 'nord'),
    ]

    @classmethod
    def clean_formid(cls, formid: str) -> str:
        """Очищает FormID до 8 hex-символов в нижнем регистре."""
        if not formid:
            return ""
        fid = str(formid).strip().split(":")[0].lower()
        return fid.zfill(8) if len(fid) < 8 else fid[-8:]

    @classmethod
    def classify(
        cls,
        race_formid_or_name: str = "",
        voice_str: str = "",
        keywords: Optional[List[str]] = None,
        npc_editorid: str = "",
    ) -> Optional[DialectProfile]:
        """
        4-уровневая детекция диалекта расы:
          1. VoiceType (VTYP)
          2. Прямой FormID ванильной расы
          3. Keywords (KWDA)
          4. Семантика EditorID / Name (субрасы и кастомные расы модов)
        Возвращает DialectProfile или None (если стандартный стиль).
        """
        race_str = str(race_formid_or_name or "").strip()
        voice = str(voice_str or "").strip().lower()
        kw_list = [k.lower() for k in (keywords or [])]
        edid = str(npc_editorid or "").strip().lower()

        # -------------------------------------------------------------
        # Уровень 1: VoiceType (VTYP) — Самый надежный маркер озвучки
        # -------------------------------------------------------------
        if voice:
            for pattern, dialect_id in cls.VOICE_PATTERNS:
                if re.search(pattern, voice, re.IGNORECASE):
                    return DIALECT_PROFILES.get(dialect_id)

        # -------------------------------------------------------------
        # Уровень 2: FormID ванильной расы
        # -------------------------------------------------------------
        clean_fid = cls.clean_formid(race_str)
        if clean_fid in cls.VANILLA_RACE_FORMIDS:
            dialect_id = cls.VANILLA_RACE_FORMIDS[clean_fid]
            return DIALECT_PROFILES.get(dialect_id)

        # -------------------------------------------------------------
        # Уровень 3: Ключевые слова (KWDA / Keywords)
        # -------------------------------------------------------------
        for kw in kw_list:
            for pattern, dialect_id in cls.SUBRACE_PATTERNS:
                if re.search(pattern, kw, re.IGNORECASE):
                    return DIALECT_PROFILES.get(dialect_id)

        # -------------------------------------------------------------
        # Уровень 4: Семантический анализ расы, субрасы и EditorID
        # -------------------------------------------------------------
        combined_text = f"{race_str} {edid}".lower()
        for pattern, dialect_id in cls.SUBRACE_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return DIALECT_PROFILES.get(dialect_id)

        # Safe Fallback: стандартная речь
        return None

    @classmethod
    def get_prompt_instructions(cls, dialect_profile: Optional[DialectProfile]) -> str:
        """Возвращает форматированную инструкцию для добавления в промпт ИИ."""
        if not dialect_profile:
            return ""
        return f"\n[СТИЛЬ СПИКЕРА: {dialect_profile.emoji} {dialect_profile.display_name.upper()}]\n{dialect_profile.system_directive}\n"
