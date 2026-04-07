import tempfile
import unittest

from doobielogic.assistant import CannabisOpsAssistant
from doobielogic.knowledge import CannabisKnowledgeBase


class TestAssistant(unittest.TestCase):
    def test_chat_returns_actions_and_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = CannabisKnowledgeBase(db_path=f"{tmp}/k.db")
            assistant = CannabisOpsAssistant(kb)
            out = assistant.chat("How should retail buyers handle open-to-buy?", persona="buyer", limit=4)
            self.assertGreater(len(out.answer), 10)
            self.assertGreater(len(out.suggested_actions), 0)
            self.assertGreater(len(out.citations), 0)


if __name__ == "__main__":
    unittest.main()
