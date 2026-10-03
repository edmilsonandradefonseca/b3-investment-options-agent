import pytest
from b3_agent.agents.reasoning import _parse_assessments


def assessment(identifier='A'):
    return {'alternative_id':identifier, 'supporting_evidence':['Observed source fact'], 'contradicting_evidence':[], 'decision_implications':['Conditional interpretation'], 'unknowns':['Target unavailable'], 'evidence_refs':['quote:1']}


def test_interpretations_are_typed_and_linked_without_numeric_metrics():
    result = _parse_assessments([assessment()], ['A','B'])
    assert result[0].alternative_id == 'A'
    assert result[0].unknowns == ('Target unavailable',)
    assert not hasattr(result[0], 'expected_return')
    assert _parse_assessments([], ['A']) == ()  # old model responses remain compatible


@pytest.mark.parametrize('values',[[assessment('invented')], [assessment(),assessment()], [{'alternative_id':'A', 'supporting_evidence':42}]])
def test_foreign_duplicate_and_malformed_model_alternatives_are_rejected(values):
    with pytest.raises(ValueError):
        _parse_assessments(values, ['A','B'])
