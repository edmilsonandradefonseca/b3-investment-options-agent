from dataclasses import replace
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from b3_agent.orchestration.contracts import OrchestratorRequest
from b3_agent.routing.lab_position import position_intent, resolve_position
from b3_agent.schemas.position import PortfolioContext, Position

TODAY = date(2026, 10, 6)
POSITION = Position('btg:PETRK376', 'PETRK376', 'OPTION', -2500,
                    strike=37.6, expiration_date=date(2026, 11, 20), option_type='CALL',
                    underlying_ticker='PETR4', source_ref='btg:portfolio.xlsx:row-5')
PORTFOLIO = PortfolioContext(TODAY, (POSITION,))


def resolve(inputs, portfolio=PORTFOLIO):
    return resolve_position({'option_id': 'PETRK376', **inputs}, portfolio, revision='current-sha', today=TODAY)


def test_identity_and_quantity_are_separate_and_no_lot_is_assumed():
    result = resolve({})
    selection = result['lab_position_selection']
    assert result['lab_clarification']['missing_fields'] == ['quantity_units']
    assert selection['side'] == 'SHORT'
    assert selection['available_quantity_units'] == 2500
    assert 'selected_quantity_units' not in selection
    assert selection['position']['source_ref'] == POSITION.source_ref
    assert selection['portfolio_revision'] == 'current-sha'
    assert result['telemetry'] == {'llm_calls': 0, 'option_chain_calls': 0}


@pytest.mark.parametrize('inputs,selected,remaining', [
    ({'quantity_units': 125}, 125, 2375),
    ({'whole_position': True}, 2500, 0),
])
def test_explicit_selection_preserves_snapshot(inputs, selected, remaining):
    result = resolve(inputs)
    selection = result['lab_position_selection']
    assert selection['selected_quantity_units'] == selected
    assert selection['remaining_quantity_units'] == remaining
    assert selection['operation_calculated'] is False
    assert selection['execution_authorized'] is False
    assert PORTFOLIO.positions[0].quantity == -2500


@pytest.mark.parametrize('quantity', [True, 0, -1, 1.5, float('nan'), float('inf'), 2501, '100'])
def test_invalid_or_excess_quantity_rejected(quantity):
    with pytest.raises(ValueError):
        resolve({'quantity_units': quantity})


def test_conflicting_units_and_whole_position_rejected():
    with pytest.raises(ValueError):
        resolve({'quantity_units': 100, 'whole_position': True})


@pytest.mark.parametrize('portfolio,missing', [
    (None, 'current_portfolio'),
    (replace(PORTFOLIO, quality_status='REJECTED'), 'current_portfolio'),
    (replace(PORTFOLIO, as_of=TODAY + timedelta(days=1)), 'current_portfolio'),
    (replace(PORTFOLIO, positions=()), 'position_identity'),
    (replace(PORTFOLIO, positions=(POSITION, POSITION)), 'position_identity'),
    (replace(PORTFOLIO, positions=(replace(POSITION, expiration_date=TODAY-timedelta(days=1)),)), 'position_identity'),
    (replace(PORTFOLIO, positions=(replace(POSITION, source_ref=''),)), 'position_identity'),
])
def test_unreconciled_position_never_substituted(portfolio, missing):
    result = resolve({'whole_position': True}, portfolio)
    assert result['lab_clarification']['missing_fields'] == [missing]
    assert 'selected_quantity_units' not in result['lab_position_selection']


def test_followup_uses_prior_intent_but_resolves_new_snapshot():
    question = 'Vale manter, encerrar ou rolar uma opção da minha carteira?'
    context = {'workspace': 'Strategy Lab', 'lab_request_kind': 'follow_up',
               'lab_conversation': [{'question': question, 'response': {'lab_clarification': {'original_question': question}}}]}
    inputs = position_intent(OrchestratorRequest('A opção é PETRK376.', context=context))
    result = resolve(inputs)
    context['lab_conversation'].append({'question': 'A opção é PETRK376.', 'response': result})
    inputs = position_intent(OrchestratorRequest('Toda a posição.', context=context))
    new = replace(PORTFOLIO, positions=(replace(POSITION, quantity=-1500),))
    selected = resolve(inputs, new)['lab_position_selection']
    assert selected['selected_quantity_units'] == 1500
    assert selected['position']['quantity'] == -1500


@pytest.mark.parametrize('task,context', [
    ('Explique como rolar PETRK376.', {'workspace': 'Strategy Lab'}),
    ('Quero encerrar PETRK376.', {'workspace': 'Market Intelligence'}),
    ('Tenho R$ 10 mil. Comprar ITUB4 ou BBDC4?', {'workspace': 'Strategy Lab'}),
])
def test_other_intents_not_intercepted(task, context):
    assert position_intent(OrchestratorRequest(task, context=context)) is None


def test_http_selection_precedes_providers_and_reads_current_snapshot(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from b3_agent import server
    from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
    from types import SimpleNamespace
    current = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    snapshot = replace(PORTFOLIO, as_of=current,
                       positions=(replace(POSITION, expiration_date=current+timedelta(days=30)),))
    (tmp_path/'imports').mkdir()
    (tmp_path/'imports'/'portfolio.xlsx').write_bytes(b'current test snapshot')
    monkeypatch.setattr(server, 'settings', SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(BtgRendaVariavelLoader, 'load', lambda self, path: snapshot)
    def unexpected(*args, **kwargs):
        raise AssertionError('Position selection must not acquire or synthesize')
    for name in ('_configure_runtime', '_dispatch_fast_route', '_dispatch_opportunity_screen', '_workspace_intelligence_response'):
        monkeypatch.setattr(server, name, unexpected)
    client = TestClient(server.app)
    response = client.post('/orchestrate', json={'task': 'Quero encerrar PETRK376.', 'context': {'workspace': 'Strategy Lab'}})
    assert response.status_code == 200
    assert response.json()['status'] == 'NEEDS_CLARIFICATION'
    response = client.post('/orchestrate', json={'task': 'Quero encerrar PETRK376, 100 unidades.', 'context': {'workspace': 'Strategy Lab'}})
    assert response.status_code == 200
    assert response.json()['status'] == 'INPUTS_IDENTIFIED'
    assert response.json()['result']['lab_position_selection']['selected_quantity_units'] == 100
    response = client.post('/orchestrate', json={'task': 'Quero encerrar PETRK376, 2501 unidades.', 'context': {'workspace': 'Strategy Lab'}})
    assert response.status_code == 400


@pytest.mark.parametrize('question', ['Quero encerrar PETRK376, -100 unidades.', 'Quero encerrar PETRK376, 1,5 unidades.'])
def test_natural_quantity_does_not_lose_sign_or_fraction(question):
    inputs = position_intent(OrchestratorRequest(question, context={'workspace': 'Strategy Lab'}))
    with pytest.raises(ValueError):
        resolve(inputs)


def test_multiple_quantities_not_silently_selected():
    with pytest.raises(ValueError):
        position_intent(OrchestratorRequest('Quero encerrar PETRK376, 100 unidades ou 200 unidades.', context={'workspace': 'Strategy Lab'}))


@pytest.mark.parametrize('changes', [{'strike': float('nan')}, {'option_type': 'UNKNOWN'}, {'underlying_ticker': None}, {'quantity': -1.5}])
def test_incomplete_snapshot_identity_requires_reconciliation(changes):
    result = resolve({'whole_position': True}, replace(PORTFOLIO, positions=(replace(POSITION, **changes),)))
    assert result['lab_clarification']['missing_fields'] == ['position_identity']
