import pytest

from b3_agent.orchestration.contracts import OrchestratorRequest
from b3_agent.routing import FastRouter, RouteTarget
from b3_agent.routing.decision_intent import explicit_stock_comparison


def test_explicit_copilot_comparison_uses_canonical_engine_without_stale_selection():
    request = OrchestratorRequest('Compare comprar ações ITUB4 e comprar ações BBDC4. Use dados atuais.', ticker='PETR4', context={'workspace':'Market Intelligence','selected_ticker':'PETR4','analysis_mode':'deterministic','as_of':'2026-10-02T18:00:00Z'})
    parsed = explicit_stock_comparison(request)
    assert parsed.ticker is None and parsed.context['selected_ticker'] is None
    assert parsed.context['comparison_assets'] == ['ITUB4','BBDC4']
    assert parsed.context['as_of'] == request.context['as_of']
    assert parsed.context['analysis_mode'] == 'deterministic'
    assert parsed.task == request.task
    assert request.context['workspace'] == 'Market Intelligence'
    assert FastRouter().route(parsed.task,metadata=parsed.context).target == RouteTarget.STRATEGY_ENGINE


@pytest.mark.parametrize('task',[
    'Não compare comprar ações ITUB4 e comprar ações BBDC4.',
    'Compare vender PUT ITUB4 e comprar ações BBDC4.',
    'Compare comprar ações ITUB4 e comprar ações BBDC4 com R$ 80000.',
    'Compare comprar ações ITUB4 e comprar ações BBDC4 ou VALE3.',
    'Compare comprar ações ITUB4 e comprar ações ITUB4.',
    'Compare comprar ações ITUB4 e comprar ações BBDC4 versus manter.',
    'Analise ITUB4 e BBDC4.',
])
def test_ambiguous_or_unsupported_intent_keeps_existing_path(task):
    request = OrchestratorRequest(task,context={'workspace':'Opportunities'})
    assert explicit_stock_comparison(request) is request


def test_structured_form_always_wins_over_text():
    request = OrchestratorRequest('Compare comprar ações ITUB4 e comprar ações BBDC4.',context={'comparison_assets':['VALE3','RENT3']})
    assert explicit_stock_comparison(request) is request


@pytest.mark.parametrize('amount,expected', [('10 mil',10000), ('10.000',10000), ('10000',10000), ('1.234,56',1234.56)])
def test_lab_explicit_natural_budget_reaches_deterministic_builder(amount, expected):
    request = OrchestratorRequest(f'Tenho R$ {amount}. Comprar ITUB4 ou BBDC4?', context={'workspace':'Strategy Lab'})
    result = explicit_stock_comparison(request)
    assert result.context['comparison_amount'] == expected
    assert result.context['comparison_assets'] == ['ITUB4', 'BBDC4']
    assert FastRouter().route(result.task, metadata=result.context).target == RouteTarget.STRATEGY_ENGINE


@pytest.mark.parametrize('text', [
    'Tenho R$ 10 mil. Comprar ITUB4 ou vender PUT BBDC4?',
    'Tenho R$ 0. Comprar ITUB4 ou BBDC4?',
    'Tenho R$ 10 mil. Comprar ITUB4 ou ITUB4?',
    'Se eu tivesse R$ 10 mil. Comprar ITUB4 ou BBDC4?',
    'Tenho R$ 10 mil. Comprar ITUB4 ou BBDC4? Ou VALE3?',
])
def test_lab_never_guesses_complex_budget_or_alternatives(text):
    request = OrchestratorRequest(text, context={'workspace':'Strategy Lab'})
    assert explicit_stock_comparison(request) is request
