from doobielogic.module_curriculum import MODULE_CURRICULA, curriculum_prompt, get_module_curriculum


EXPECTED_MODULES = {
    "buyer",
    "inventory",
    "retail_ops",
    "cultivation",
    "extraction",
    "kitchen",
    "packaging",
    "compliance",
    "ops",
    "executive",
    "copilot",
}


def test_every_operational_module_has_a_complete_curriculum():
    assert EXPECTED_MODULES <= set(MODULE_CURRICULA)
    for curriculum in MODULE_CURRICULA.values():
        assert curriculum.purpose
        assert curriculum.core_topics
        assert curriculum.key_metrics
        assert curriculum.decision_rules
        assert curriculum.required_evidence
        assert curriculum.safe_failure


def test_curriculum_prompt_instructs_evidence_and_safe_failure():
    prompt = curriculum_prompt("cultivation")
    assert "Required evidence:" in prompt
    assert "Safe failure:" in prompt
    assert "pesticide" in prompt.lower()


def test_unknown_module_fails_to_conservative_copilot_curriculum():
    assert get_module_curriculum("unknown").mode == "copilot"

