from doobielogic.evals import apply_low_confidence_fallback, evaluate_doobie_response


def test_evaluate_doobie_response_flags_issues():
    result = evaluate_doobie_response({
        'answer': '',
        'explanation': '',
        'recommendations': [],
        'confidence': 'high',
        'sources': [],
    }, context={'relevant_rules': ['buyer_doh_low']})
    assert result['pass'] is False
    assert result['score'] < 100


def test_low_confidence_fallback_preserves_useful_guidance():
    out = apply_low_confidence_fallback({
        'answer': 'Review hourly basket components before changing staffing.',
        'explanation': 'Compare units, price, discounts, and stockouts.',
        'recommendations': ['do x'],
        'confidence': 'low',
        'sources': [],
        'mode': 'buyer',
    })
    assert out['answer'].startswith('Review hourly basket')
    assert out['confidence'] == 'low'
    assert len(out['recommendations']) >= 1


def test_low_confidence_fallback_replaces_only_empty_or_placeholder_answers():
    out = apply_low_confidence_fallback({
        'answer': 'guess',
        'explanation': '',
        'recommendations': [],
        'confidence': 'low',
        'sources': [],
        'mode': 'buyer',
    })
    assert out['answer'].startswith('I need a little more operating context')
    assert out['recommendations']
