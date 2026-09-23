"""
🐾 Unit Tests for Speaker & Gender Context Analyzer.
"""

import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.speaker_analyzer import SpeakerAnalyzer, SpeakerContext
from src.narrative_context import NarrativeContextBuffer


class TestSpeakerAnalyzer(unittest.TestCase):

    def test_extract_gender_from_flags(self):
        self.assertEqual(SpeakerAnalyzer.extract_gender_from_flags("Female, Essential"), "female")
        self.assertEqual(SpeakerAnalyzer.extract_gender_from_flags("Essential, Unique"), "male")
        self.assertEqual(SpeakerAnalyzer.extract_gender_from_flags(""), "male")
        self.assertEqual(SpeakerAnalyzer.extract_gender_from_flags(None), "male")

    def test_build_npc_registry(self):
        raw_npcs = [
            {
                "type": "Npc",
                "formid": "002F99:Rafaela.esp",
                "editorid": "RafaelaAngelic",
                "fields": [
                    {"path": "Name", "value": "Rafaela"},
                    {"path": "Configuration.Flags", "value": "Female, Essential, Unique"},
                    {"path": "Race", "value": "005749:Rafaela.esp"}
                ]
            },
            {
                "type": "Npc",
                "formid": "000869:Skyrim.esm",
                "editorid": "JarlBalgruuf",
                "fields": [
                    {"path": "Name", "value": "Balgruuf the Greater"},
                    {"path": "Configuration.Flags", "value": "Essential, Unique"},
                ]
            }
        ]
        registry = SpeakerAnalyzer.build_npc_registry(raw_npcs)
        
        self.assertIn("002f99:rafaela.esp", registry["by_formid"])
        self.assertEqual(registry["by_formid"]["002f99:rafaela.esp"]["gender"], "female")
        self.assertEqual(registry["by_formid"]["002f99:rafaela.esp"]["name"], "Rafaela")

        self.assertIn("000869:skyrim.esm", registry["by_formid"])
        self.assertEqual(registry["by_formid"]["000869:skyrim.esm"]["gender"], "male")

    def test_enrich_items_dialogue_roles_and_gender(self):
        raw_records = [
            {
                "type": "Npc",
                "formid": "002F99:Rafaela.esp",
                "editorid": "RafaelaAngelic",
                "fields": [
                    {"path": "Name", "value": "Rafaela"},
                    {"path": "Configuration.Flags", "value": "Female, Essential"}
                ]
            }
        ]

        items = [
            # 1. Сам NPC
            {
                "formid": "002F99:Rafaela.esp",
                "type": "Npc",
                "editorid": "RafaelaAngelic",
                "path": "Name",
                "text": "Rafaela"
            },
            # 2. Вопрос игрока к Рафаэле (Prompt)
            {
                "formid": "005958:Rafaela.esp",
                "type": "DialogResponses",
                "editorid": "",
                "path": "Prompt",
                "text": "Could you show that pretty body of yours?",
                "fields": [
                    {"path": "*parent.EditorID", "value": "aaRafaelaDialogueHumanNakedTopic"},
                    {"path": "Conditions", "value": "Data.Function=GetIsID | Data.Parameter1=002F99:Rafaela.esp"}
                ]
            },
            # 3. Ответ Рафаэлы игроку (Responses)
            {
                "formid": "005958:Rafaela.esp",
                "type": "DialogResponses",
                "editorid": "",
                "path": "Responses[0].Text",
                "text": "Let me think about it...",
                "fields": [
                    {"path": "*parent.EditorID", "value": "aaRafaelaDialogueHumanNakedTopic"},
                    {"path": "Conditions", "value": "Data.Function=GetIsID | Data.Parameter1=002F99:Rafaela.esp"}
                ]
            }
        ]

        enriched = SpeakerAnalyzer.enrich_items_with_speaker_context(items, raw_records)

        # Проверка NPC
        self.assertEqual(enriched[0]["speaker_context"]["gender"], "female")
        self.assertEqual(enriched[0]["speaker_context"]["badge"], "♀ Rafaela")

        # Проверка Prompt игрока
        self.assertEqual(enriched[1]["speaker_context"]["role"], "player")
        self.assertEqual(enriched[1]["speaker_context"]["target_gender"], "female")
        self.assertEqual(enriched[1]["speaker_context"]["addressing"], "Rafaela")
        self.assertIn("👤 Игрок ➔ ♀ Rafaela", enriched[1]["speaker_context"]["badge"])

        # Проверка ответа NPC
        self.assertEqual(enriched[2]["speaker_context"]["role"], "npc")
        self.assertEqual(enriched[2]["speaker_context"]["gender"], "female")
        self.assertEqual(enriched[2]["speaker_context"]["speaker_name"], "Rafaela")
        self.assertIn("🗣️ ♀ Rafaela", enriched[2]["speaker_context"]["badge"])

    def test_narrative_context_prompt_gender_instructions(self):
        buffer = NarrativeContextBuffer()
        items = [
            {
                "id": 1,
                "type": "DialogResponses",
                "path": "Responses[0].Text",
                "text": "I was really glad to see you again!",
                "speaker_context": {
                    "role": "npc",
                    "speaker_name": "Rafaela",
                    "gender": "female",
                    "addressing": "Player"
                }
            },
            {
                "id": 2,
                "type": "DialogResponses",
                "path": "Prompt",
                "text": "Are you ready for battle?",
                "speaker_context": {
                    "role": "player",
                    "speaker_name": "Player",
                    "gender": "neutral",
                    "addressing": "Rafaela",
                    "target_gender": "female"
                }
            }
        ]

        packages = buffer.build_contextual_packages(items)
        prompt = buffer.format_prompt_for_packages(packages)

        self.assertIn("ИНСТРУКЦИИ ПО ПЕРЕВОДУ, ГРАММАТИКЕ И СТИЛИСТИКЕ:", prompt)
        self.assertIn("ЖЕНСКИЙ РОД СПИКЕРА", prompt)
        self.assertIn("ОБРАЩЕНИЕ К ЖЕНЩИНЕ", prompt)


if __name__ == "__main__":
    unittest.main()
