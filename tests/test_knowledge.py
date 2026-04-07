import tempfile
import unittest

from doobielogic.knowledge import CannabisKnowledgeBase


class TestKnowledgeBase(unittest.TestCase):
    def test_knowledge_query_returns_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = CannabisKnowledgeBase(db_path=f"{tmp}/knowledge.db")
            result = kb.ask("What is limonene terpene used for?", limit=3)
            self.assertIn("answer", result)
            self.assertGreater(len(result["matches"]), 0)

    def test_feedback_learning_inserts_playbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = CannabisKnowledgeBase(db_path=f"{tmp}/knowledge.db")
            kb.learn_from_feedback("buyer", "How to run weekly buying review?", "Use vendor scorecards and open-to-buy controls.", True)
            result = kb.ask("weekly buying review vendor scorecards", limit=10)
            self.assertTrue(any(m["category"] == "playbook" for m in result["matches"]))

    def test_categories_non_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = CannabisKnowledgeBase(db_path=f"{tmp}/knowledge.db")
            cats = kb.categories()
            self.assertIn("terpene", cats)
            self.assertIn("cannabinoid", cats)


if __name__ == "__main__":
    unittest.main()
