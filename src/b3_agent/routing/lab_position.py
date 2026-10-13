"""Resolve explicit Lab position management against the current snapshot only."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
import math
import re
import unicodedata

from b3_agent.orchestration.contracts import OrchestratorRequest
from b3_agent.schemas.position import PortfolioContext


def _text(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', value.upper()) if not unicodedata.combining(c))


def position_intent(request: OrchestratorRequest) -> dict | None:
    if request.context.get('workspace') != 'Strategy Lab' or any(request.context.get(k) for k in ('comparison_assets', 'funded_switch', 'put_candidate_option_ids')):
        return None
    explicit = request.context.get('lab_position_inputs')
    if explicit is not None:
        if not isinstance(explicit, dict):
            raise ValueError('lab_position_inputs must be an object')
        return dict(explicit)
    text = _text(request.task)
    if re.search(r'\b(EXPLIQUE|TESE|EVIDENCIAS|COMO FUNCIONA)\b', text):
        return None
    previous = request.context.get('lab_conversation') or []
    prior = None
    if request.context.get('lab_request_kind') == 'follow_up' and isinstance(previous, list):
        for turn in reversed(previous):
            response = turn.get('response', {}) if isinstance(turn, dict) else {}
            if isinstance(response, dict) and (response.get('lab_clarification') or response.get('lab_position_selection')):
                prior = turn
                break
    intent_text = text
    if prior is not None:
        # Prior text supplies user intent, never portfolio facts or prices.
        intent_text += ' ' + _text(str(prior.get('question', '')))
        response = prior['response']
        clarification = response.get('lab_clarification') or {}
        intent_text += ' ' + _text(str(clarification.get('original_question', '')))
        if response.get('lab_position_selection'):
            intent_text += ' MANTER'  # Continue the explicitly selected management request.
    if not re.search(r'\b(ROLAR|ROLAGEM|ENCERRAR|FECHAR|RECOMPRAR|MANTER)\b', intent_text):
        return None
    ids = re.findall(r'\b[A-Z]{4}[A-X]\d{1,6}\b', text)
    option_id = ids[0] if len(set(ids)) == 1 else None
    if not option_id and prior is not None:
        selection = prior['response'].get('lab_position_selection') or {}
        option_id = selection.get('option_id')
    if not option_id:
        return None  # Existing no-contract clarification handles this case.
    matches = re.findall(r'(?<![\w.,])([+-]?\d+(?:[.,]\d+)?)\s*UNIDADES?\b', text)
    if len(matches) > 1:
        raise ValueError('Specify one quantity in broker snapshot units')
    quantity = float(matches[0].replace(',', '.')) if matches else None
    return {'option_id': option_id,
            'quantity_units': quantity,
            'whole_position': bool(re.search(r'\b(TODA A POSICAO|POSICAO INTEIRA|POSICAO INTEGRAL)\b', text)),
            'action': 'COMPARE_POSITION_MANAGEMENT'}


def resolve_position(inputs: dict, portfolio: PortfolioContext | None, *, revision: str | None, today: date) -> dict:
    option_id = str(inputs.get('option_id', '')).strip().upper()
    if re.fullmatch(r'[A-Z]{4}[A-X]\d{1,6}', option_id) is None:
        raise ValueError('An exact option identifier is required')
    selection = {'policy_version': 'lab-current-position-v1', 'option_id': option_id,
                 'portfolio_revision': revision, 'status': 'NOT_RESOLVED',
                 'execution_authorized': False, 'operation_calculated': False}
    def ask(field, question, reason):
        return {'lab_position_selection': selection,
                'lab_clarification': {'status': 'NEEDS_CLARIFICATION', 'missing_fields': [field], 'question': question, 'reason': reason},
                'summary': question, 'derived_synthesis_status': 'NOT_REQUESTED',
                'telemetry': {'llm_calls': 0, 'option_chain_calls': 0}}
    if portfolio is None or portfolio.quality_status == 'REJECTED' or portfolio.as_of > today:
        return ask('current_portfolio', 'Qual é a posição vigente desse contrato?', 'O snapshot atual não está disponível ou não é admissível; nenhuma posição anterior foi reutilizada.')
    matches = [p for p in portfolio.positions if p.instrument_type.upper() == 'OPTION' and p.ticker.upper() == option_id]
    if len(matches) != 1:
        return ask('position_identity', 'Esse contrato está na carteira vigente? Confira o código da posição.', 'O snapshot não contém uma identidade única; não foi escolhida outra opção do mesmo ativo.')
    position = matches[0]
    if (not math.isfinite(position.quantity) or position.quantity != int(position.quantity)
            or not math.isfinite(position.contract_multiplier) or not position.source_ref
            or position.strike is None or not math.isfinite(position.strike) or position.strike <= 0
            or position.option_type not in {'CALL', 'PUT'}
            or not position.underlying_ticker
            or position.expiration_date is None or position.expiration_date < today):
        return ask('position_identity', 'A posição desse contrato continua aberta?', 'A identidade, origem ou vigência da posição precisa ser reconciliada antes da operação.')
    selection.update(status='POSITION_IDENTIFIED', position=asdict(position), snapshot_as_of=portfolio.as_of,
                     side='SHORT' if position.quantity < 0 else 'LONG',
                     available_quantity_units=abs(position.quantity), quantity_basis='BROKER_SNAPSHOT_UNITS',
                     contract_identity_status='SNAPSHOT_IDENTITY; PROVIDER_CONFIRMATION_PENDING')
    quantity = inputs.get('quantity_units')
    whole = inputs.get('whole_position', False)
    if not isinstance(whole, bool):
        raise ValueError('whole_position must be boolean')
    if whole and quantity is not None:
        raise ValueError('Specify units or whole_position, not both')
    if whole:
        quantity = abs(position.quantity)
    if quantity is None:
        return ask('quantity_units', 'Deseja analisar toda a posição ou quantas unidades?', 'Informe “toda a posição” ou a quantidade em unidades do extrato. Não foi assumida uma operação integral nem um lote de 100.')
    if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity <= 0 or quantity != int(quantity):
        raise ValueError('Quantity must be a positive integer in broker snapshot units')
    if quantity > abs(position.quantity):
        raise ValueError('Selected quantity exceeds the current position')
    selection.update(status='POSITION_AND_QUANTITY_IDENTIFIED', selected_quantity_units=int(quantity),
                     remaining_quantity_units=abs(position.quantity)-quantity,
                     quantity_selection='EXPLICIT_WHOLE_POSITION' if whole else 'EXPLICIT_UNITS')
    return {'lab_position_selection': selection,
            'summary': 'Posição e quantidade identificadas no snapshot vigente. Cotações, custos e alternativas de encerramento/rolagem ainda precisam ser calculados.',
            'derived_synthesis_status': 'NOT_REQUESTED',
            'telemetry': {'llm_calls': 0, 'option_chain_calls': 0}}
