"""
🐾 Unit Tests for SkyUI MCM Translation Manager.
"""

import unittest
import sys
import codecs
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.mcm_manager import MCMManager, MCMEntry
from src.quality_gate import QualityGate


class TestMCMManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_and_parse_mcm_utf16le_bom(self):
        sample_file = self.test_dir / "SampleMod_ENGLISH.txt"
        lines = [
            "$SAMPLE_HEADER\tSample Mod Configuration",
            "$SAMPLE_OPT_POWER\tSpell Power Multiplier",
            "$SAMPLE_OPT_DESC\tIncreases spell power by %d%% across all spells.",
        ]
        content = "\r\n".join(lines) + "\r\n"
        with open(sample_file, "w", encoding="utf-16", newline="") as f:
            f.write(content)

        entries, enc = MCMManager.read_mcm_lines(sample_file)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].key, "$SAMPLE_HEADER")
        self.assertEqual(entries[0].text, "Sample Mod Configuration")
        self.assertEqual(entries[1].key, "$SAMPLE_OPT_POWER")
        self.assertEqual(entries[1].text, "Spell Power Multiplier")

        items = MCMManager.parse_mcm_file(sample_file, "SampleMod")
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["type"], "MCM")
        self.assertEqual(items[0]["formid"], "MCM:$SAMPLE_HEADER")
        self.assertEqual(items[0]["speaker_context"]["badge"], "⚙️ $SAMPLE_HEADER")

    def test_export_russian_mcm_utf16le_bom(self):
        review_entries = [
            {
                "id": 1,
                "formid": "MCM:$SAMPLE_HEADER",
                "type": "MCM",
                "path": "$SAMPLE_HEADER",
                "original": "Sample Mod Configuration",
                "translated": "Настройки примера мода"
            },
            {
                "id": 2,
                "formid": "MCM:$SAMPLE_OPT_POWER",
                "type": "MCM",
                "path": "$SAMPLE_OPT_POWER",
                "original": "Spell Power Multiplier",
                "translated": "Множитель силы заклинаний"
            },
            {
                "id": 3,
                "formid": "MCM:$SAMPLE_OPT_DESC",
                "type": "MCM",
                "path": "$SAMPLE_OPT_DESC",
                "original": "Increases spell power by %d%%.",
                "translated": "Увеличивает силу заклинаний на %d%%."
            },
            # Строка брони (не MCM) - не должна попасть в MCM файл
            {
                "id": 4,
                "formid": "000800:SampleMod.esp",
                "type": "Armor",
                "path": "Name",
                "original": "Iron Armor",
                "translated": "Железная броня"
            }
        ]

        out_path = MCMManager.export_russian_mcm(review_entries, "SampleMod", out_dir=self.test_dir)
        self.assertIsNotNone(out_path)
        self.assertTrue(out_path.exists())
        self.assertEqual(out_path.name, "SampleMod_RUSSIAN.txt")

        # Проверяем BOM байты (0xFF, 0xFE для UTF-16 LE)
        raw_bytes = out_path.read_bytes()
        self.assertTrue(raw_bytes.startswith(codecs.BOM_UTF16_LE))

        # Читаем обратно и проверяем пары $KEY \t Перевод
        entries, _ = MCMManager.read_mcm_lines(out_path)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].key, "$SAMPLE_HEADER")
        self.assertEqual(entries[0].text, "Настройки примера мода")
        self.assertEqual(entries[1].key, "$SAMPLE_OPT_POWER")
        self.assertEqual(entries[1].text, "Множитель силы заклинаний")
        self.assertEqual(entries[2].key, "$SAMPLE_OPT_DESC")
        self.assertEqual(entries[2].text, "Увеличивает силу заклинаний на %d%%.")

    def test_mcm_quality_gate_validation(self):
        # Валидная запись MCM
        valid_entry = {
            "id": 1,
            "formid": "MCM:$FMR_PAGE1",
            "type": "MCM",
            "field": "$FMR_PAGE1",
            "original": "General Options",
            "translated": "Основные настройки",
            "source": "mcm"
        }
        issue = QualityGate.validate_entry(valid_entry)
        self.assertIsNone(issue)

        # Запись с утечкой латиницы
        leak_entry = {
            "id": 2,
            "formid": "MCM:$FMR_PAGE2",
            "type": "MCM",
            "field": "$FMR_PAGE2",
            "original": "Advanced Spell Options",
            "translated": "Продвинутые Spell настройки",
            "source": "mcm"
        }
        issue = QualityGate.validate_entry(leak_entry)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.issue_type, "language_leak")


if __name__ == "__main__":
    unittest.main()
