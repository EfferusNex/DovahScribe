"""
🐾 Unit Tests for Global Glossary & Lore Terminology Engine.
"""

import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.glossary import GlobalGlossary, TESCanonSeed, GlossaryExtractor
from src.narrative_context import NarrativeContextBuffer
from src.quality_gate import QualityGate


class TestGlobalGlossary(unittest.TestCase):

    def setUp(self):
        self.glossary = GlobalGlossary()

    def test_seed_terms_loaded(self):
        self.assertIn("Alteration", self.glossary.terms)
        self.assertEqual(self.glossary.terms["Alteration"]["ru"], "Изменение")
        self.assertIn("Mehrunes Dagon", self.glossary.terms)
        self.assertEqual(self.glossary.terms["Mehrunes Dagon"]["ru"], "Мерунес Дагон")
        self.assertIn("Dragonborn", self.glossary.terms)

    def test_term_matching(self):
        text = "Increases Alteration spell duration and grants favor with Mehrunes Dagon in Whiterun."
        matches = self.glossary.find_matching_terms(text)
        self.assertIn("Alteration", matches)
        self.assertIn("Mehrunes Dagon", matches)
        self.assertIn("Whiterun", matches)
        self.assertEqual(matches["Alteration"], "Изменение")
        self.assertEqual(matches["Mehrunes Dagon"], "Мерунес Дагон")
        self.assertEqual(matches["Whiterun"], "Вайтран")

    def test_add_custom_term(self):
        self.glossary.add_term("Phantom Shroud", "Призрачный покров", category="SPEL", source_mod="test_mod")
        self.assertEqual(self.glossary.get_term("Phantom Shroud"), "Призрачный покров")
        matches = self.glossary.find_matching_terms("Cast Phantom Shroud to become invisible.")
        self.assertIn("Phantom Shroud", matches)
        self.assertEqual(matches["Phantom Shroud"], "Призрачный покров")

    def test_extractor_populate(self):
        sample_items = [
            {"type": "SPEL", "path": "Name", "text": "Arcane Volley", "translated": "Тайный залп", "formid": "01001A"},
            {"type": "PERK", "path": "Name", "text": "Pyromancer", "translated": "Пиромант", "formid": "01001B"},
            {"type": "INFO", "path": "RNAM", "text": "Hello traveler", "translated": "Привет, путник", "formid": "01001C"}
        ]
        added = GlossaryExtractor.populate_from_items(sample_items, "SampleMod", self.glossary)
        self.assertEqual(added, 2)
        self.assertEqual(self.glossary.get_term("Arcane Volley"), "Тайный залп")
        self.assertEqual(self.glossary.get_term("Pyromancer"), "Пиромант")

    def test_narrative_context_injection(self):
        buffer = NarrativeContextBuffer(window_size=2)
        sample_items = [
            {"id": 1, "text": "Cast an Alteration ward near Solitude.", "type": "SPEL", "path": "DESC"}
        ]
        packages = buffer.build_contextual_packages(sample_items)
        prompt = buffer.format_prompt_for_packages(packages)
        self.assertIn("ОБЯЗАТЕЛЬНЫЙ ГЛОССАРИЙ", prompt)
        self.assertIn("Alteration", prompt)
        self.assertIn("Изменение", prompt)
        self.assertIn("Solitude", prompt)
        self.assertIn("Солитьюд", prompt)

    def test_quality_gate_glossary_consistency(self):
        # 1. Correct translation (inflected)
        orig = "Empowers Alteration magic in Whiterun."
        trans_correct = "Усиливает магию школы Изменения в Вайтране."
        mismatches = QualityGate.check_glossary_consistency(orig, trans_correct)
        self.assertEqual(len(mismatches), 0)

        # 2. Inconsistent / wrong translation
        trans_wrong = "Усиливает магию модификации в Белом городе."
        mismatches = QualityGate.check_glossary_consistency(orig, trans_wrong)
        self.assertTrue(len(mismatches) >= 1)
        mismatched_terms = [m[0] for m in mismatches]
        self.assertIn("Alteration", mismatched_terms)


if __name__ == "__main__":
    unittest.main()
