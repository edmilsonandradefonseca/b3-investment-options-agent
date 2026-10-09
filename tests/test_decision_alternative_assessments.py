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


def test_decision_schema_requires_structured_coverage_only_for_supplied_alternatives():
    from b3_agent.agents.reasoning import InvestmentReasoningAgent
    from b3_agent.agents.context import AgentContext
    class Model:
        schemas = []
        def complete_json(self, **kwargs):
            self.schemas.append(kwargs['schema'])
            return dict(action='WAIT',subject_id='A',thesis='Unknown',rationale='Conditional',evidence_refs=[],risks=[],opportunity_cost='Unknown',capital_impact='Unknown',confidence='UNKNOWN',invalidation_conditions=[],alternative_assessments=[assessment()] if 'alternative_assessments' in kwargs['schema']['properties'] else [])
    model = Model()
    agent = InvestmentReasoningAgent(model)
    agent.decide(AgentContext(request='Compare', deterministic_context={'workspace_result':{'strategy_comparison':{'alternatives':[{'alternative_id':'A'}]}}}))
    schema = model.schemas[-1]
    assert 'alternative_assessments' in schema['required']
    assert schema['properties']['alternative_assessments']['items']['properties']['alternative_id']['enum'] == ['A']
    assert set(schema['properties']) == set(schema['required'])
    agent.decide(AgentContext(request='Status'))
    schema = model.schemas[-1]
    assert 'alternative_assessments' not in schema['properties']
    assert set(schema['properties']) == set(schema['required'])
