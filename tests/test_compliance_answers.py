from doobielogic.compliance_answers import answer_verified_compliance_question


def test_massachusetts_new_adult_use_daily_limit_is_grounded():
    result = answer_verified_compliance_question(
        "what is the new daily limit for adult use purchases?",
        "MA",
    )
    assert result is not None
    assert "2 ounces" in result["answer"]
    assert "10 grams" in result["answer"]
    assert "1,000 milligrams" in result["answer"]
    assert result["confidence"] == "high"
    assert result["rule_verified"] is True
    assert result["sources"][0].startswith("Massachusetts Cannabis Control Commission")


def test_unverified_jurisdiction_does_not_invent_a_limit():
    assert answer_verified_compliance_question("What is the purchase limit?", "CA") is None
