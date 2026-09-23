"""
🐾 Speaker & Gender Context Analyzer (Анализ пола говорящего, расы и диалекта).
Определяет:
  1. Пол, расу и тип голоса персонажей мода (записи NPC_ / Npc).
  2. Ролевую принадлежность строк диалогов (Игрок 'Prompt' vs NPC 'Responses[*].Text').
  3. Расовый диалект (каджиты, аргониане, даэдра, орки, данмеры) через DialectClassifier.
  4. Кому адресована реплика и стилистические директивы для ИИ.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from src.dialect_engine import DialectClassifier, DialectProfile, DIALECT_PROFILES


class SpeakerContext:
    """Контекст говорящего и адресата для реплики или сущности."""

    def __init__(
        self,
        role: str = "unknown",          # "npc", "player", "item", "system"
        speaker_name: str = "",
        gender: str = "unknown",        # "female", "male", "neutral", "unknown"
        race: str = "",                 # Исходная раса/FormID
        race_display: str = "",         # Красивое название расы ("Каджит", "Аргонианин")
        dialect_type: str = "standard", # "khajiit", "argonian", "daedric", "orc", "dunmer", "nord", "standard"
        style_directive: str = "",      # Инструкция для ИИ
        addressing: str = "",           # Кому адресована реплика (например, "Rafaela (female)")
        target_gender: str = "unknown", # Пол адресата
        source_formid: str = "",
        badge: str = "",
    ):
        self.role = role
        self.speaker_name = speaker_name
        self.gender = gender
        self.race = race
        self.race_display = race_display
        self.dialect_type = dialect_type
        self.style_directive = style_directive
        self.addressing = addressing
        self.target_gender = target_gender
        self.source_formid = source_formid
        self.badge = badge

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "speaker_name": self.speaker_name,
            "gender": self.gender,
            "race": self.race,
            "race_display": self.race_display,
            "dialect_type": self.dialect_type,
            "style_directive": self.style_directive,
            "addressing": self.addressing,
            "target_gender": self.target_gender,
            "source_formid": self.source_formid,
            "badge": self.badge,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpeakerContext':
        return cls(
            role=data.get("role", "unknown"),
            speaker_name=data.get("speaker_name", ""),
            gender=data.get("gender", "unknown"),
            race=data.get("race", ""),
            race_display=data.get("race_display", ""),
            dialect_type=data.get("dialect_type", "standard"),
            style_directive=data.get("style_directive", ""),
            addressing=data.get("addressing", ""),
            target_gender=data.get("target_gender", "unknown"),
            source_formid=data.get("source_formid", ""),
            badge=data.get("badge", ""),
        )


class SpeakerAnalyzer:
    """
    Анализатор гендерного, расового и диалогового контекста персонажей.
    """

    @classmethod
    def extract_gender_from_flags(cls, flags_val: Any) -> str:
        """Определяет пол по значению флагов Configuration.Flags или ACBS."""
        if not flags_val:
            return "male"  # В Skyrim при отсутствии флага Female по умолчанию пол мужской
        str_flags = str(flags_val).lower()
        if "female" in str_flags:
            return "female"
        return "male"

    @classmethod
    def build_npc_registry(cls, raw_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Сканирует список сырых записей и строит реестр всех NPC плагина с расами и диалектами.
        Ключи: FormID, EditorID (lower), Name (lower).
        """
        registry: Dict[str, Dict[str, Any]] = {
            "by_formid": {},
            "by_editorid": {},
            "by_name": {},
        }

        for rec in raw_records:
            r_type = rec.get("type", "")
            if r_type not in ["Npc", "NPC_"]:
                continue

            formid = rec.get("formid", "")
            editorid = rec.get("editorid", "")
            fields = rec.get("fields", [])

            name = ""
            flags_val = ""
            race = ""
            voice = ""
            keywords: List[str] = []

            for f in fields:
                f_path = f.get("path", "")
                val = f.get("value")
                if f_path in ["Name", "ShortName"] and val and not name:
                    name = str(val).strip()
                elif "Flags" in f_path:
                    flags_val = str(val)
                elif f_path == "Race":
                    race = str(val)
                elif f_path == "Voice":
                    voice = str(val)
                elif "Keywords" in f_path and val:
                    if isinstance(val, list):
                        keywords.extend([str(k) for k in val])
                    else:
                        keywords.append(str(val))

            # Если запись передана в плоском формате
            if not name and "Name" in rec:
                name = str(rec.get("Name", "")).strip()
            if not flags_val and "Configuration.Flags" in rec:
                flags_val = str(rec.get("Configuration.Flags", ""))
            if not race and "Race" in rec:
                race = str(rec.get("Race", ""))
            if not voice and "Voice" in rec:
                voice = str(rec.get("Voice", ""))

            gender = cls.extract_gender_from_flags(flags_val)

            # Определяем диалект через DialectClassifier
            dialect_profile = DialectClassifier.classify(
                race_formid_or_name=race,
                voice_str=voice,
                keywords=keywords,
                npc_editorid=editorid,
            )

            dialect_type = dialect_profile.dialect_id if dialect_profile else "standard"
            race_display = dialect_profile.display_name if dialect_profile else (race or "")
            style_directive = dialect_profile.system_directive if dialect_profile else ""
            dialect_emoji = dialect_profile.emoji if dialect_profile else ""

            npc_data = {
                "formid": formid,
                "editorid": editorid,
                "name": name or editorid or "Unknown NPC",
                "gender": gender,
                "race": race,
                "race_display": race_display,
                "voice": voice,
                "dialect_type": dialect_type,
                "style_directive": style_directive,
                "dialect_emoji": dialect_emoji,
            }

            if formid:
                registry["by_formid"][formid.lower()] = npc_data
                short_id = formid.split(":")[0].lower()
                registry["by_formid"][short_id] = npc_data
            if editorid:
                registry["by_editorid"][editorid.lower()] = npc_data
            if name:
                registry["by_name"][name.lower()] = npc_data

        return registry

    @classmethod
    def resolve_speaker_for_dialog(
        cls,
        rec: Dict[str, Any],
        npc_registry: Dict[str, Dict[str, Any]],
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Определяет имя, пол и полные данные NPC, привязанного к диалогу.
        Возвращает (npc_name, gender, npc_data_dict).
        """
        fields = rec.get("fields", [])
        
        # 1. Проверяем поле Speaker
        for f in fields:
            if f.get("path") == "Speaker" and "value" in f:
                spk_val = str(f["value"]).strip().lower()
                if spk_val in npc_registry["by_formid"]:
                    npc = npc_registry["by_formid"][spk_val]
                    return npc["name"], npc["gender"], npc

        # 2. Проверяем Conditions (GetIsID, GetIsRace, GetIsSex)
        for f in fields:
            if "Conditions" in f.get("path", ""):
                val_str = str(f.get("value", ""))
                found_ids = re.findall(r'[0-9A-Fa-f]{6}(?::[A-Za-z0-9_\-\. ]+)?', val_str)
                for fid in found_ids:
                    fid_clean = fid.lower()
                    if fid_clean in npc_registry["by_formid"]:
                        npc = npc_registry["by_formid"][fid_clean]
                        return npc["name"], npc["gender"], npc
                    short_id = fid_clean.split(":")[0]
                    if short_id in npc_registry["by_formid"]:
                        npc = npc_registry["by_formid"][short_id]
                        return npc["name"], npc["gender"], npc

                # Проверка GetIsRace на условия диалектов
                for pattern, d_id in DialectClassifier.SUBRACE_PATTERNS:
                    if re.search(pattern, val_str, re.IGNORECASE):
                        prof = DIALECT_PROFILES.get(d_id)
                        if prof:
                            dummy_npc = {
                                "name": prof.display_name,
                                "gender": "unknown",
                                "race_display": prof.display_name,
                                "dialect_type": prof.dialect_id,
                                "style_directive": prof.system_directive,
                                "dialect_emoji": prof.emoji,
                            }
                            return prof.display_name, "unknown", dummy_npc

                # Проверка GetIsSex (1 = female, 0 = male)
                if "GetIsSex" in val_str:
                    g = "female" if ("Parameter1=1" in val_str or "ComparisonValue=1" in val_str) else "male"
                    return "NPC", g, {"name": "NPC", "gender": g, "dialect_type": "standard"}

        # 3. Эвристика по EditorID или родительскому топику (*parent.EditorID)
        parent_topic = ""
        for f in fields:
            if f.get("path") == "*parent.EditorID" and "value" in f:
                parent_topic = str(f["value"]).lower()

        for npc_name_lower, npc in npc_registry["by_name"].items():
            if len(npc_name_lower) >= 3 and npc_name_lower in parent_topic:
                return npc["name"], npc["gender"], npc

        for npc_edid_lower, npc in npc_registry["by_editorid"].items():
            if len(npc_edid_lower) >= 3 and npc_edid_lower in parent_topic:
                return npc["name"], npc["gender"], npc

        # Если в реестре всего один уникальный NPC мода
        unique_npcs = list(npc_registry["by_editorid"].values())
        if len(unique_npcs) == 1:
            return unique_npcs[0]["name"], unique_npcs[0]["gender"], unique_npcs[0]

        return "NPC", "unknown", {}

    @classmethod
    def enrich_items_with_speaker_context(
        cls,
        items: List[Dict[str, Any]],
        raw_records: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Обогащает список извлеченных строк контекстом говорящего, расы и диалекта.
        """
        records_to_scan = raw_records or items
        registry = cls.build_npc_registry(records_to_scan)

        for item in items:
            r_type = item.get("type", "")
            path = item.get("path", "")
            formid = item.get("formid", "")
            editorid = item.get("editorid", "")

            # 1. Если это сам персонаж (Npc / NPC_)
            if r_type in ["Npc", "NPC_"]:
                npc_data = registry["by_formid"].get(formid.lower()) or {}
                gender = npc_data.get("gender", "unknown")
                npc_name = item.get("text", "") or npc_data.get("name", editorid)
                d_emoji = npc_data.get("dialect_emoji", "")
                gender_sym = "♀" if gender == "female" else "♂"
                badge = f"{d_emoji} {gender_sym} {npc_name}".strip()

                ctx = SpeakerContext(
                    role="npc",
                    speaker_name=npc_name,
                    gender=gender,
                    race=npc_data.get("race", ""),
                    race_display=npc_data.get("race_display", ""),
                    dialect_type=npc_data.get("dialect_type", "standard"),
                    style_directive=npc_data.get("style_directive", ""),
                    addressing="",
                    target_gender="unknown",
                    source_formid=formid,
                    badge=badge,
                )
                item["speaker_context"] = ctx.to_dict()
                continue

            # 2. Если это диалог (DialogResponses / INFO / DialogTopic / DIAL)
            if r_type in ["DialogResponses", "INFO", "DialogTopic", "DIAL"]:
                npc_name, npc_gender, npc_data = cls.resolve_speaker_for_dialog(item, registry)
                d_emoji = npc_data.get("dialect_emoji", "")
                dialect_type = npc_data.get("dialect_type", "standard")
                style_directive = npc_data.get("style_directive", "")
                race_display = npc_data.get("race_display", "")

                gender_sym = "♀" if npc_gender == "female" else ("♂" if npc_gender == "male" else "")
                speaker_display = f"{d_emoji} {gender_sym} {npc_name}".strip()

                # Если это реплика игрока в меню диалога (Prompt)
                if path == "Prompt":
                    badge = f"👤 Игрок ➔ {speaker_display}"
                    ctx = SpeakerContext(
                        role="player",
                        speaker_name="Player",
                        gender="neutral",
                        race="",
                        race_display="",
                        dialect_type="standard",
                        style_directive="",
                        addressing=npc_name,
                        target_gender=npc_gender,
                        source_formid=formid,
                        badge=badge,
                    )
                else:
                    # Это ответная реплика NPC (Responses[*].Text)
                    badge = f"🗣️ {speaker_display}"
                    ctx = SpeakerContext(
                        role="npc",
                        speaker_name=npc_name,
                        gender=npc_gender,
                        race=npc_data.get("race", ""),
                        race_display=race_display,
                        dialect_type=dialect_type,
                        style_directive=style_directive,
                        addressing="Player",
                        target_gender="neutral",
                        source_formid=formid,
                        badge=badge,
                    )
                item["speaker_context"] = ctx.to_dict()
                continue

            # 3. Для всех остальных типов (предметы, книги, заклинания)
            ctx = SpeakerContext(
                role="item",
                speaker_name="",
                gender="neutral",
                race="",
                race_display="",
                dialect_type="standard",
                style_directive="",
                addressing="",
                target_gender="unknown",
                source_formid=formid,
                badge="",
            )
            item["speaker_context"] = ctx.to_dict()

        return items
