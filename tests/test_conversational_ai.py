from types import SimpleNamespace

from doobielogic.conversational_ai import (
    ConversationService,
    build_conversation_instructions,
)


class FakeResponses:
    def __init__(self, output_text: str = "Model-grounded cannabis answer"):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text: str = "Model-grounded cannabis answer"):
        self.responses = FakeResponses(output_text)


def test_curriculum_is_sent_as_real_model_instructions():
    client = FakeClient()
    service = ConversationService(client=client, provider="openai", model="test-model")
    result = service.enhance(
        {"answer": "Rules answer", "sources": ["https://example.gov"], "confidence": "medium"},
        question="How should I investigate room yield?",
        mode="cultivation",
        state="CA",
        data={"room": ["A"], "yield": [40]},
        history=[{"role": "user", "content": "We are reviewing room A."}],
    )
    assert result["answer"] == "Model-grounded cannabis answer"
    assert result["ai"]["enabled"] is True
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert "Specialist module: cultivation" in call["instructions"]
    assert "Required evidence:" in call["instructions"]
    assert call["input"][0]["role"] == "user"


def test_compliance_instructions_forbid_model_memory_and_require_verification():
    instructions = build_conversation_instructions("compliance", "NY")
    assert "Never fill a missing current rule from model memory" in instructions
    assert "qualified-counsel verification" in instructions
    assert "New York" in instructions


def test_rules_fallback_is_explicit_when_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = ConversationService(provider="auto")
    result = service.enhance(
        {"answer": "Rules answer"},
        question="Help",
        mode="copilot",
    )
    assert result["answer"] == "Rules answer"
    assert result["ai"]["enabled"] is False
    assert "OPENAI_API_KEY" in result["ai"]["fallback_reason"]


def test_model_failure_preserves_rules_answer():
    class BrokenResponses:
        def create(self, **kwargs):
            raise RuntimeError("provider down")

    service = ConversationService(
        client=SimpleNamespace(responses=BrokenResponses()),
        provider="openai",
    )
    result = service.enhance(
        {"answer": "Rules answer"},
        question="Help",
        mode="ops",
    )
    assert result["answer"] == "Rules answer"
    assert result["ai"]["enabled"] is False
    assert "RuntimeError" in result["ai"]["fallback_reason"]
