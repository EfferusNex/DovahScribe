"""
🐾 Тесты для модуля QualityGate & Language Leak Detector.
"""

import unittest
from src.quality_gate import QualityGate, QualityReport


class TestQualityGate(unittest.TestCase):
    def test_pure_russian_text(self):
        text = "Огненная стрела наносит 25 единиц урона пламенем."
        has_leak, leaked = QualityGate.detect_language_leak(text)
        self.assertFalse(has_leak)
        self.assertEqual(leaked, [])

    def test_pure_english_text(self):
        text = "Spectral Cloak"
        has_leak, leaked = QualityGate.detect_language_leak(text)
        self.assertTrue(has_leak)
        self.assertIn("Spectral", leaked)
        self.assertIn("Cloak", leaked)

    def test_mixed_language_leak(self):
        text = "Забытая магия: Phantom Shroud"
        has_leak, leaked = QualityGate.detect_language_leak(text)
        self.assertTrue(has_leak)
        self.assertEqual(leaked, ["Phantom", "Shroud"])

    def test_tags_and_formatting(self):
        text = "<font color='#FF0000'>Огненный шар</font> [pagebreak] <alias=Player> побеждает дракона!"
        has_leak, leaked = QualityGate.detect_language_leak(text)
        self.assertFalse(has_leak, f"Leaked words detected: {leaked}")

    def test_roman_numerals(self):
        text = "Исцеление ран IV. Том VIII священных писаний."
        has_leak, leaked = QualityGate.detect_language_leak(text)
        self.assertFalse(has_leak, f"Leaked words detected: {leaked}")

    def test_system_tokens_and_whitelisted(self):
        text = "$MCM_SETTINGS_TITLE"
        entry = {
            "id": 1,
            "formid": "0x1234",
            "field": "Name",
            "original": "$MCM_SETTINGS_TITLE",
            "translated": "$MCM_SETTINGS_TITLE",
            "source": "vanilla"
        }
        issue = QualityGate.validate_entry(entry)
        self.assertIsNone(issue)

    def test_whitelist_gaming_terms(self):
        text = "Увеличивает DPS оружия и восстанавливает 50 HP и MP."
        has_leak, leaked = QualityGate.detect_language_leak(text)
        self.assertFalse(has_leak, f"Leaked words detected: {leaked}")

    def test_tag_parity_mismatch(self):
        entry = {
            "id": 2,
            "formid": "0x5678",
            "field": "Responses[0].Text",
            "original": "Hello <alias=Player>, how are you %s?",
            "translated": "Привет, как дела?",  # Missing tags!
            "source": "lain_agent"
        }
        issue = QualityGate.validate_entry(entry)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.issue_type, "tag_mismatch")

    def test_audit_report(self):
        entries = [
            {"id": 1, "formid": "0x01", "field": "Name", "original": "Fireball", "translated": "Огненный шар"},
            {"id": 2, "formid": "0x02", "field": "Name", "original": "Frost Armor", "translated": "Frost Armor"}, # leak
            {"id": 3, "formid": "0x03", "field": "Name", "original": "Lightning Bolt", "translated": ""}, # empty
        ]
        report = QualityGate.audit_entries(entries)
        self.assertEqual(report.total_checked, 3)
        self.assertEqual(report.passed_count, 1)
        self.assertEqual(report.leaks_count, 1)
        self.assertEqual(report.empty_count, 1)
        self.assertFalse(report.is_clean)


if __name__ == "__main__":
    unittest.main()
