"""
🐾 Lore & Terminology Engine (Единый глобальный глоссарий TES и модов).
Обеспечивает сквозную консистентность терминов во всей сборке модов:
  1. Официальная каноничная база терминов TES V: Skyrim (школы магии, даэдра, материалы, расы, холды).
  2. Единый накопительный глобальный глоссарий (data/global_glossary.json).
  3. Автоматическое извлечение именованных сущностей из модов (NER).
  4. Динамический поиск терминов в переводимых текстах для передачи подсказок ИИ.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
GLOBAL_GLOSSARY_FILE = DATA_DIR / "global_glossary.json"


class TESCanonSeed:
    """Официальная каноничная база терминов The Elder Scrolls V: Skyrim."""

    SEED_TERMS: Dict[str, Dict[str, str]] = {
        # Школы магии (Schools of Magic)
        "Alteration": {"ru": "Изменение", "cat": "School"},
        "Conjuration": {"ru": "Колдовство", "cat": "School"},
        "Destruction": {"ru": "Разрушение", "cat": "School"},
        "Illusion": {"ru": "Иллюзия", "cat": "School"},
        "Restoration": {"ru": "Восстановление", "cat": "School"},
        "Enchanting": {"ru": "Зачарование", "cat": "School"},
        "Alchemy": {"ru": "Алхимия", "cat": "School"},

        # Материалы и типы экипировки
        "Iron": {"ru": "Железный", "cat": "Material"},
        "Steel": {"ru": "Стальной", "cat": "Material"},
        "Silver": {"ru": "Серебряный", "cat": "Material"},
        "Elven": {"ru": "Эльфийский", "cat": "Material"},
        "Dwarven": {"ru": "Двемерский", "cat": "Material"},
        "Orcish": {"ru": "Орочий", "cat": "Material"},
        "Ebony": {"ru": "Эбонитовый", "cat": "Material"},
        "Glass": {"ru": "Стеклянный", "cat": "Material"},
        "Dragonplate": {"ru": "Драконий панцирный", "cat": "Material"},
        "Dragonscale": {"ru": "Драконий чешуйчатый", "cat": "Material"},
        "Daedric": {"ru": "Даэдрический", "cat": "Material"},
        "Stalhrim": {"ru": "Сталгримовый", "cat": "Material"},
        "Nordic": {"ru": "Нордский", "cat": "Material"},
        "Chitin": {"ru": "Хитиновый", "cat": "Material"},
        "Bonemold": {"ru": "Костяной", "cat": "Material"},
        "Leather": {"ru": "Кожаный", "cat": "Material"},
        "Hide": {"ru": "Сыромятный", "cat": "Material"},
        "Fur": {"ru": "Меховой", "cat": "Material"},
        "Scaled": {"ru": "Пластинчатый", "cat": "Material"},
        "Corundum": {"ru": "Корунд", "cat": "Material"},
        "Malachite": {"ru": "Малахит", "cat": "Material"},
        "Moonstone": {"ru": "Лунный камень", "cat": "Material"},
        "Orichalcum": {"ru": "Орихалк", "cat": "Material"},
        "Quicksilver": {"ru": "Ртуть", "cat": "Material"},

        # Даэдрические Принцы (Daedric Princes)
        "Azura": {"ru": "Азура", "cat": "Daedra"},
        "Boethiah": {"ru": "Боэтия", "cat": "Daedra"},
        "Clavicus Vile": {"ru": "Клавикус Вайл", "cat": "Daedra"},
        "Hermaeus Mora": {"ru": "Хермеус Мора", "cat": "Daedra"},
        "Hircine": {"ru": "Хирсин", "cat": "Daedra"},
        "Malacath": {"ru": "Малакат", "cat": "Daedra"},
        "Mehrunes Dagon": {"ru": "Мерунес Дагон", "cat": "Daedra"},
        "Mephala": {"ru": "Мефала", "cat": "Daedra"},
        "Meridia": {"ru": "Меридия", "cat": "Daedra"},
        "Molag Bal": {"ru": "Молаг Бал", "cat": "Daedra"},
        "Namira": {"ru": "Намира", "cat": "Daedra"},
        "Nocturnal": {"ru": "Ноктюрнал", "cat": "Daedra"},
        "Peryite": {"ru": "Периайт", "cat": "Daedra"},
        "Sanguine": {"ru": "Сангвин", "cat": "Daedra"},
        "Sheogorath": {"ru": "Шеогорат", "cat": "Daedra"},
        "Vaermina": {"ru": "Вермина", "cat": "Daedra"},
        "Jyggalag": {"ru": "Джиггалаг", "cat": "Daedra"},

        # Девять Божеств (The Nine Divines)
        "Akatosh": {"ru": "Акатош", "cat": "Divine"},
        "Arkay": {"ru": "Аркей", "cat": "Divine"},
        "Dibella": {"ru": "Дибелла", "cat": "Divine"},
        "Julianos": {"ru": "Джулианос", "cat": "Divine"},
        "Kynareth": {"ru": "Кинарет", "cat": "Divine"},
        "Mara": {"ru": "Мара", "cat": "Divine"},
        "Stendarr": {"ru": "Стендарр", "cat": "Divine"},
        "Talos": {"ru": "Талос", "cat": "Divine"},
        "Zenithar": {"ru": "Зенитар", "cat": "Divine"},

        # Расы (Races)
        "Altmer": {"ru": "Альтмер", "cat": "Race"},
        "Bosmer": {"ru": "Босмер", "cat": "Race"},
        "Dunmer": {"ru": "Данмер", "cat": "Race"},
        "Falmer": {"ru": "Фалмер", "cat": "Race"},
        "Orsimer": {"ru": "Орсимер", "cat": "Race"},
        "Argonian": {"ru": "Аргонианин", "cat": "Race"},
        "Khajiit": {"ru": "Каджит", "cat": "Race"},
        "Breton": {"ru": "Бретонец", "cat": "Race"},
        "Nord": {"ru": "Норд", "cat": "Race"},
        "Imperial": {"ru": "Имперец", "cat": "Race"},
        "Redguard": {"ru": "Редгард", "cat": "Race"},

        # Владения и города Скайрима (Holds & Cities)
        "Whiterun": {"ru": "Вайтран", "cat": "Location"},
        "Solitude": {"ru": "Солитьюд", "cat": "Location"},
        "Windhelm": {"ru": "Виндхельм", "cat": "Location"},
        "Riften": {"ru": "Рифтен", "cat": "Location"},
        "Markarth": {"ru": "Маркарт", "cat": "Location"},
        "Falkreath": {"ru": "Фолкрит", "cat": "Location"},
        "Morthal": {"ru": "Морфал", "cat": "Location"},
        "Dawnstar": {"ru": "Данстар", "cat": "Location"},
        "Winterhold": {"ru": "Винтерхолд", "cat": "Location"},
        "Riverwood": {"ru": "Ривервуд", "cat": "Location"},
        "Rorikstead": {"ru": "Рорикстед", "cat": "Location"},
        "Ivarstead": {"ru": "Айварстед", "cat": "Location"},
        "Dragon Bridge": {"ru": "Драконий Мост", "cat": "Location"},
        "Helgen": {"ru": "Хелген", "cat": "Location"},
        "High Hrothgar": {"ru": "Высокий Хротгар", "cat": "Location"},
        "Throat of the World": {"ru": "Глотка Мира", "cat": "Location"},
        "Bleak Falls Barrow": {"ru": "Ветреный пик", "cat": "Location"},
        "Sovngarde": {"ru": "Совнгард", "cat": "Location"},
        "Soul Cairn": {"ru": "Каирн Душ", "cat": "Location"},
        "Apocrypha": {"ru": "Апокриф", "cat": "Location"},
        "Blackreach": {"ru": "Черный Предел", "cat": "Location"},

        # Фракции (Factions)
        "Companions": {"ru": "Соратники", "cat": "Faction"},
        "College of Winterhold": {"ru": "Коллегия Винтерхолда", "cat": "Faction"},
        "Thieves Guild": {"ru": "Гильдия воров", "cat": "Faction"},
        "Dark Brotherhood": {"ru": "Темное Братство", "cat": "Faction"},
        "Imperial Legion": {"ru": "Имперский легион", "cat": "Faction"},
        "Stormcloaks": {"ru": "Братья Бури", "cat": "Faction"},
        "Greybeards": {"ru": "Седобородые", "cat": "Faction"},
        "Blades": {"ru": "Клинки", "cat": "Faction"},
        "Dawnguard": {"ru": "Стражи Рассвета", "cat": "Faction"},
        "Volkihar Clan": {"ru": "Клан Волкихар", "cat": "Faction"},
        "Forsworn": {"ru": "Изгои", "cat": "Faction"},
        "Silver Hand": {"ru": "Серебряная Рука", "cat": "Faction"},
        "Vigilants of Stendarr": {"ru": "Дозорные Стендарра", "cat": "Faction"},
        "Thalmor": {"ru": "Талмор", "cat": "Faction"},
        "Nightingales": {"ru": "Соловьи", "cat": "Faction"},
        "Bards College": {"ru": "Коллегия бардов", "cat": "Faction"},

        # Понятия и механики
        "Race": {"ru": "Раса", "cat": "Concept"},
        "Races": {"ru": "Расы", "cat": "Concept"},
        "Staff": {"ru": "Посох", "cat": "Item"},
        "Follower": {"ru": "Спутник", "cat": "Concept"},
        "Hostile": {"ru": "Враждебный", "cat": "Concept"},
        "Dragonborn": {"ru": "Драконорождённый", "cat": "Mechanic"},
        "Dovahkiin": {"ru": "Довакин", "cat": "Mechanic"},
        "Thu'um": {"ru": "Ту'ум", "cat": "Mechanic"},
        "Shout": {"ru": "Крик", "cat": "Mechanic"},
        "Word of Power": {"ru": "Слово Силы", "cat": "Mechanic"},
        "Magicka": {"ru": "Магия", "cat": "Mechanic"},
        "Stamina": {"ru": "Запас сил", "cat": "Mechanic"},
        "Health": {"ru": "Здоровье", "cat": "Mechanic"},
        "Soul Gem": {"ru": "Камень душ", "cat": "Mechanic"},
        "Black Soul Gem": {"ru": "Черный камень душ", "cat": "Mechanic"},
        "Elder Scroll": {"ru": "Древний свиток", "cat": "Mechanic"},
        "Jarl": {"ru": "Ярл", "cat": "Title"},
        "Thane": {"ru": "Тан", "cat": "Title"},
        "Housecarl": {"ru": "Хускарл", "cat": "Title"},
    }


class GlobalGlossary:
    """
    Единый накопительный глобальный глоссарий терминов Skyrim.
    Хранится в data/global_glossary.json.
    """

    _instance: Optional['GlobalGlossary'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalGlossary, cls).__new__(cls)
            cls._instance._init_glossary()
        return cls._instance

    def _init_glossary(self):
        self.filepath = GLOBAL_GLOSSARY_FILE
        self.terms: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        # 1. Сначала загружаем сиды канона TES
        for en, data in TESCanonSeed.SEED_TERMS.items():
            self.terms[en] = {
                "en": en,
                "ru": data["ru"],
                "category": data["cat"],
                "source_mod": "TES_Canon"
            }

        # 2. Если файл глобального глоссария существует — накладываем пользовательские и накопленные термины
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    terms_data = file_data.get("terms", file_data)
                    if isinstance(terms_data, dict):
                        for en, entry in terms_data.items():
                            if isinstance(entry, dict) and "ru" in entry:
                                self.terms[en] = entry
                            elif isinstance(entry, str):
                                self.terms[en] = {"en": en, "ru": entry, "category": "custom", "source_mod": "user"}
            except Exception:
                pass
        else:
            self.save()

    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "total_terms": len(self.terms),
                "description": "Единый глобальный глоссарий терминов TES V: Skyrim и модов"
            },
            "terms": self.terms
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def add_term(
        self,
        en_term: str,
        ru_term: str,
        category: str = "mod_entity",
        source_mod: str = "common",
        formid: str = ""
    ):
        """Добавляет или обновляет термин в едином глобальном глоссарии."""
        clean_en = en_term.strip()
        clean_ru = ru_term.strip()
        if not clean_en or not clean_ru or clean_en == clean_ru:
            return

        self.terms[clean_en] = {
            "en": clean_en,
            "ru": clean_ru,
            "category": category,
            "source_mod": source_mod,
            "formid": formid
        }

    def get_term(self, en_term: str) -> Optional[str]:
        """Возвращает русский перевод термина."""
        clean = en_term.strip()
        entry = self.terms.get(clean)
        return entry["ru"] if entry else None

    def find_matching_terms(self, text: str) -> Dict[str, str]:
        """
        Ищет термины из единого глоссария внутри переданного текста.
        Возвращает словарь { 'English Term': 'Русский перевод' }, отсортированный от длинных к коротким.
        """
        if not text:
            return {}

        matches: Dict[str, str] = {}
        # Сортируем ключи по убыванию длины для корректного матчинга составных фраз
        sorted_keys = sorted(self.terms.keys(), key=lambda x: len(x), reverse=True)

        for en_key in sorted_keys:
            if len(en_key) < 3:
                continue
            # Поиск слова или словосочетания с учетом границ слов
            pattern = r'\b' + re.escape(en_key) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                matches[en_key] = self.terms[en_key]["ru"]

        return matches


class GlossaryExtractor:
    """
    Экстрактор именованных сущностей из мода в единый глоссарий.
    """

    PRIORITY_TYPES: Set[str] = {
        "SPEL", "Spell",
        "PERK", "Perk",
        "MGEF", "MagicEffect",
        "NPC_", "Npc",
        "FACT", "Faction",
        "LCTN", "Location",
        "SHOU", "Shout",
        "ARMO", "Armor",
        "WEAP", "Weapon",
    }

    @classmethod
    def populate_from_items(
        cls,
        items: List[Dict[str, Any]],
        mod_name: str,
        global_glossary: Optional[GlobalGlossary] = None,
    ) -> int:
        """
        Сканирует ключевые записи мода и пополняет единый глоссарий терминами.
        """
        glossary = global_glossary or GlobalGlossary()
        added = 0

        for item in items:
            r_type = item.get("type", "")
            path = item.get("path", "")
            text = item.get("text", "").strip()
            translated = item.get("translated", "").strip()
            formid = item.get("formid", "")

            if r_type in cls.PRIORITY_TYPES and path in ["Name", "ShortName"]:
                if not text or len(text) < 2:
                    continue

                if translated and translated != text:
                    glossary.add_term(
                        en_term=text,
                        ru_term=translated,
                        category=r_type,
                        source_mod=mod_name,
                        formid=formid
                    )
                    added += 1

        glossary.save()
        return added
