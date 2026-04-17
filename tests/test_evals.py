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


def test_low_confidence_fallback_applies_safe_response():
    out = apply_low_confidence_fallback({
        'answer': 'guess',
        'explanation': 'maybe',
        'recommendations': ['do x'],
        'confidence': 'low',
        'sources': [],
        'mode': 'buyer',
    })
    assert out['answer'].startswith('Insufficient confidence')
    assert out['confidence'] == 'low'
    assert len(out['recommendations']) >= 1
