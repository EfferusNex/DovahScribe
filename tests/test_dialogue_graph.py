import unittest
from src.narrative_context import DialogueGraphBuilder

class TestDialogueGraphBuilder(unittest.TestCase):
    def test_build_dialogue_graph_hierarchy(self):
        items = [
            {
                "id": 1,
                "formid": "00013E",
                "type": "QUST",
                "original": "Escape from Helgen",
                "translated": "Побег из Хелгена"
            },
            {
                "id": 2,
                "formid": "000801",
                "type": "DIAL",
                "field": "Prompt",
                "original": "How did you escape?",
                "translated": "Как ты выбрался?",
                "parent_context": {"quest_id": "00013E", "quest_name": "Побег из Хелгена"}
            },
            {
                "id": 3,
                "formid": "000802",
                "type": "INFO",
                "original": "We took the keep dungeon and the cave pass.",
                "translated": "Мы прошли через темницу крепости и пещеры.",
                "parent_context": {"quest_id": "00013E", "topic_id": "000801"},
                "speaker_context": {"speaker_name": "Ralof", "gender": "male"}
            }
        ]

        graph = DialogueGraphBuilder.build_graph(items)
        self.assertEqual(graph["total_dialogue_lines"], 1)
        self.assertEqual(len(graph["quests"]), 1)
        
        quest = graph["quests"][0]
        self.assertEqual(quest["quest_id"], "00013E")
        self.assertEqual(quest["quest_name"], "Побег из Хелгена")
        self.assertEqual(len(quest["topics"]), 1)
        
        topic = quest["topics"][0]
        self.assertEqual(topic["topic_id"], "000801")
        self.assertEqual(topic["prompt_translated"], "Как ты выбрался?")
        self.assertEqual(len(topic["responses"]), 1)
        
        resp = topic["responses"][0]
        self.assertEqual(resp["entry_id"], 3)
        self.assertEqual(resp["speaker"], "Ralof")
        self.assertEqual(resp["gender"], "male")

if __name__ == "__main__":
    unittest.main()
