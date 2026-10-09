"""Bounded explicit stock comparison input; no LLM or financial inference."""
from __future__ import annotations

import re
import unicodedata

from b3_agent.orchestration.contracts import OrchestratorRequest

_STOCK_COMPARISON = re.compile(
    r'^(?:UC-04:\s*)?COMPARE\s+COMPRAR\s+ACOES?\s+'
    r'([A-Z]{4}\d{1,2})\s+(?:E|VERSUS|VS\.?|X)\s+'
    r'(?:COMPRAR\s+ACOES?\s+)?([A-Z]{4}\d{1,2})(?=[\s.,;!?]|$)'
)
_BUDGET_COMPARISON = re.compile(
    r'^TENHO\s+R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)'
    r'\s*(MIL)?\s*\.\s*COMPRAR\s+([A-Z]{4}\d{1,2})\s+OU\s+([A-Z]{4}\d{1,2})\s*\?$'
)
_UNSUPPORTED = re.compile(r'\b(?:PUT|CALL|OPCOES|OPCAO|VENDER|REDUZIR|MANTER|ROLAR)\b|R\$|\b\d+(?:[.,]\d+)?\s*(?:MIL|REAIS)\b')


def explicit_stock_comparison(request: OrchestratorRequest) -> OrchestratorRequest:
    """Promote only an explicit two-stock BUY comparison to the UC-04 builder.

    Structured forms win. Complex actions/budgets require their own deterministic
    parser and are left to the existing senior path, never guessed here.
    A stale sidebar selection does not add a third comparison alternative.
    """
    if any(key in request.context for key in ('comparison_assets', 'put_candidate_option_ids', 'strategy_a', 'strategy_b')):
        return request
    text = ''.join(c for c in unicodedata.normalize('NFD', request.task.upper()) if not unicodedata.combining(c))
    budget_match = _BUDGET_COMPARISON.fullmatch(text.strip())
    if budget_match and request.context.get('workspace') == 'Strategy Lab':
        amount, thousands, left, right = budget_match.groups()
        budget = float(amount.replace('.', '').replace(',', '.')) * (1000 if thousands else 1)
        if left != right and budget > 0:
            return OrchestratorRequest(task=request.task, ticker=None, context={
                **request.context, 'selected_ticker': None,
                'comparison_assets': [left, right], 'comparison_amount': budget,
                'strategy_a': 'Comprar ação', 'strategy_b': 'Comprar ação',
                'decision_intent': {'status': 'MATCH_EXACT', 'policy_version': 'B3_EXPLICIT_BUDGET_COMPARISON_V1'},
            })
    match = _STOCK_COMPARISON.match(text)
    if not match or _UNSUPPORTED.search(text):
        return request
    assets = list(match.groups())
    mentioned = set(re.findall(r'(?<![A-Z0-9])([A-Z]{4}\d{1,2})(?![A-Z0-9])', text))
    if len(set(assets)) != 2 or mentioned != set(assets):
        return request
    context = {
        **request.context,
        'origin_workspace': request.context.get('workspace'),
        'workspace': 'Strategy Lab', 'selected_ticker': None,
        'comparison_assets': assets,
        'strategy_a': 'Comprar ação', 'strategy_b': 'Comprar ação',
        'decision_intent': {'status': 'MATCH_EXACT', 'policy_version': 'B3_EXPLICIT_STOCK_BUY_COMPARISON_V1'},
    }
    return OrchestratorRequest(task=request.task, ticker=None, context=context)
