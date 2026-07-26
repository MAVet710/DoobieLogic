from doobielogic.intelligence_router import infer_intelligence_route


def test_routes_specialist_questions_without_a_mode_selector():
    examples = {
        "What should I reorder before we stock out?": "buyer",
        "How should I schedule budtenders for store traffic?": "retail_ops",
        "How can I improve cultivation yield by room?": "cultivation",
        "Why did extraction yield fall on this solvent run?": "extraction",
        "How should I investigate edible batch potency variance?": "kitchen",
        "Which label controls belong in packaging line clearance?": "packaging",
        "What state rule applies to cannabis transport?": "compliance",
        "whats the new daily limit for adult use purchases": "compliance",
        "Give leadership a company-wide margin review.": "executive",
        "Where is the operating bottleneck?": "ops",
    }
    for question, expected in examples.items():
        assert infer_intelligence_route(question).mode == expected


def test_compliance_language_takes_priority_when_legally_material():
    route = infer_intelligence_route("Is this packaging label compliant with state law?")
    assert route.mode == "compliance"


def test_generic_substrings_do_not_trigger_legal_route():
    assert infer_intelligence_route("Show the workflow flaws").mode == "ops"


def test_uploaded_columns_route_when_question_is_ambiguous():
    route = infer_intelligence_route("Review this", data={"input_weight": [100], "output_weight": [8]})
    assert route.mode == "extraction"
