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


class FakeGroqCompletions:
    def __init__(self, output_text: str = "## Direct answer\nGrounded Groq answer"):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.output_text))]
        )


class FakeGroqClient:
    def __init__(self, output_text: str = "## Direct answer\nGrounded Groq answer"):
        self.chat = SimpleNamespace(completions=FakeGroqCompletions(output_text))


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


def test_instructions_forbid_expanding_source_summaries_into_law():
    instructions = build_conversation_instructions("packaging", "NY")
    assert "proves only the facts explicitly written" in instructions
    assert "never expand it into unstated mandated warnings" in instructions
    assert "rule_verified=true" in instructions


def test_unverified_compliance_answer_uses_official_domain_web_search():
    client = FakeClient()
    service = ConversationService(client=client, provider="openai", model="test-model")
    service.enhance(
        {"answer": "Rules answer", "sources": [], "confidence": "low"},
        question="What is the current purchase limit?",
        mode="compliance",
        state="MA",
    )
    call = client.responses.calls[0]
    assert call["tools"][0]["type"] == "web_search"
    assert "masscannabiscontrol.com" in call["tools"][0]["filters"]["allowed_domains"]
    assert call["include"] == ["web_search_call.action.sources"]


def test_verified_compliance_answer_does_not_spend_on_web_search():
    client = FakeClient()
    service = ConversationService(client=client, provider="openai", model="test-model")
    service.enhance(
        {"answer": "Verified answer", "rule_verified": True},
        question="What is the current purchase limit?",
        mode="compliance",
        state="MA",
    )
    assert "tools" not in client.responses.calls[0]


def test_rules_fallback_is_explicit_when_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    service = ConversationService(provider="auto")
    result = service.enhance(
        {"answer": "Rules answer"},
        question="Help",
        mode="copilot",
    )
    assert result["answer"].startswith("Rules answer")
    assert result["ai"]["enabled"] is False
    assert "GROQ_API_KEY" in result["ai"]["fallback_reason"]
    assert "**To make this actionable**" in result["answer"]


def test_groq_is_a_first_class_conversation_provider():
    client = FakeGroqClient()
    service = ConversationService(client=client, provider="groq", model="test-groq")
    result = service.enhance(
        {
            "answer": "Rules answer",
            "recommendations": ["Inspect approved artwork", "Reconcile labels"],
            "sources": ["[module_curriculum:packaging]"],
            "confidence": "medium",
        },
        question="What packaging controls should I verify in New York?",
        mode="packaging",
        state="NY",
    )

    assert result["answer"].startswith("## Direct answer")
    assert result["ai"] == {
        "provider": "groq",
        "model": "test-groq",
        "enabled": True,
        "fallback_reason": None,
    }
    call = client.chat.completions.calls[0]
    assert call["model"] == "test-groq"
    assert call["messages"][0]["role"] == "system"
    assert "RESPONSE CONTRACT" in call["messages"][0]["content"]
    assert "https://cannabis.ny.gov/plma" in str(call["messages"])
    assert "summary_only" in str(call["messages"])
    assert result["retrieval"]["status"] == "curated_evidence_match"
    assert all(source.startswith("http") for source in result["sources"])


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
    assert result["answer"].startswith("Rules answer")
    assert result["ai"]["enabled"] is False
    assert "RuntimeError" in result["ai"]["fallback_reason"]

