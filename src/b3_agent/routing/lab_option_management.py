"""Current-position option management with explicit execution-side pricing.

All returned monetary amounts are gross incremental cash flows. They are never
labelled profit/return. Provider quotes are point-in-time checked before use.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import math
import re
import unicodedata
from typing import Any

from b3_agent.orchestration.contracts import OrchestratorRequest
from b3_agent.schemas.position import PortfolioContext, Position

_POLICY = "lab-option-management-v1"
_CODE = re.compile(r"\b[A-Z]{4}[A-X]\d{1,6}\b")


def _normal(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value.upper()) if not unicodedata.combining(c))


def management_intent(request: OrchestratorRequest) -> dict[str, Any] | None:
    """Promote only a continuation that already has an exact identified position."""
    if request.context.get("workspace") != "Strategy Lab":
        return None
    explicit = request.context.get("lab_option_management")
    if explicit is not None:
        if not isinstance(explicit, dict):
            raise ValueError("lab_option_management must be an object")
        return dict(explicit)
    if request.context.get("lab_request_kind") != "follow_up":
        return None
    turns = request.context.get("lab_conversation") or []
    prior = next((turn for turn in reversed(turns) if isinstance(turn, dict)
                  and isinstance(turn.get("response"), dict)
                  and turn["response"].get("lab_position_selection")), None)
    if prior is None:
        return None
    selected = prior["response"]["lab_position_selection"]
    if selected.get("status") != "POSITION_AND_QUANTITY_IDENTIFIED":
        return None
    text = _normal(request.task)
    old_id = str(selected.get("option_id", "")).upper()
    codes = list(dict.fromkeys(_CODE.findall(text)))
    candidate_ids = {str(item.get("option_id", "")).upper()
                     for item in prior["response"].get("lab_roll_candidates", []) if isinstance(item, dict)}
    choosing_displayed_candidate = len(codes) == 1 and codes[0] in candidate_ids
    if not re.search(r"\b(MANTER|ENCERRAR|FECHAR|RECOMPRAR|ROLAR|ROLAGEM|COMPARAR)\b", text) and not choosing_displayed_candidate:
        return None
    destinations = [code for code in codes if code != old_id]
    if len(destinations) > 1:
        raise ValueError("Informe apenas um contrato de destino para a rolagem")
    return {"option_id": old_id, "quantity_units": selected.get("selected_quantity_units"),
            "destination_option_id": destinations[0] if destinations else None,
            "action": "COMPARE_KEEP_CLOSE_ROLL"}


def _valid_contract_quote(contract: Any, quote: Any, *, option_id: str,
                          underlying: str, option_type: str, strike: float | None,
                          expiration: Any, as_of: datetime) -> None:
    if contract is None or quote is None:
        raise ValueError(f"No current OPLAB contract and quote for {option_id}")
    if contract.option_id.upper() != option_id or quote.option_id.upper() != option_id:
        raise ValueError("OPLAB returned an ambiguous contract or quote identity")
    if contract.underlying_ticker.upper() != underlying or quote.ticker.upper() != underlying:
        raise ValueError("OPLAB contract/quote underlying does not match the BTG position")
    if contract.option_type.upper() != option_type:
        raise ValueError("OPLAB contract type does not match the BTG position")
    if strike is not None and abs(float(contract.strike) - float(strike)) > 1e-6:
        raise ValueError("OPLAB strike does not match the BTG position")
    if expiration is not None and contract.expiration_date != expiration:
        raise ValueError("OPLAB expiry does not match the BTG position")
    observed = quote.observation_timestamp
    available = quote.available_timestamp
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    if available.tzinfo is None:
        available = available.replace(tzinfo=timezone.utc)
    cutoff = as_of.astimezone(timezone.utc)
    if observed > cutoff or available > cutoff or observed < cutoff - timedelta(days=7):
        raise ValueError("OPLAB quote is outside the admissible seven-day current window")
    if quote.quality_status in {"REJECTED", "INVALID"} or not quote.source:
        raise ValueError("OPLAB quote is not admissible")
    if not math.isfinite(contract.contract_multiplier) or contract.contract_multiplier <= 0:
        raise ValueError("OPLAB contract multiplier is missing or invalid")
    if quote.bid is not None and (not math.isfinite(quote.bid) or quote.bid <= 0):
        raise ValueError("OPLAB bid is invalid")
    if quote.ask is not None and (not math.isfinite(quote.ask) or quote.ask <= 0):
        raise ValueError("OPLAB ask is invalid")
    if quote.bid is not None and quote.ask is not None and quote.ask < quote.bid:
        raise ValueError("OPLAB bid/ask market is crossed")


def _leg(contract: Any, quote: Any, *, trade_side: str, quantity: int) -> dict[str, Any]:
    field = "ask" if trade_side == "BUY" else "bid"
    price = getattr(quote, field)
    flow = None if price is None else round((1 if trade_side == "SELL" else -1) * price * contract.contract_multiplier * quantity, 8)
    return {"contract_id": contract.option_id, "underlying": contract.underlying_ticker,
            "option_type": contract.option_type, "strike": contract.strike,
            "expiration_date": contract.expiration_date.isoformat(), "trade_side": trade_side,
            "quantity_contract_units": quantity, "contract_multiplier": contract.contract_multiplier,
            "price_field": field, "price_brl_per_underlying_unit": price,
            "gross_incremental_cash_flow_brl": flow,
            "quote_as_of": quote.observation_timestamp.isoformat(), "source": quote.source,
            "source_record_id": quote.source_record_id}


def compare_management(*, position: Position, quantity_units: int,
                       old_contract: Any, old_quote: Any,
                       new_contract: Any | None, new_quote: Any | None,
                       portfolio: PortfolioContext, portfolio_revision: str,
                       as_of: datetime, transaction_costs_brl: float | None = None) -> dict[str, Any]:
    """Build keep/close/roll alternatives without turning premiums into profit."""
    if isinstance(quantity_units, bool) or not isinstance(quantity_units, int) or quantity_units <= 0 or quantity_units > abs(position.quantity):
        raise ValueError("Selected quantity must be a positive integer no larger than the current position")
    if transaction_costs_brl is not None and (isinstance(transaction_costs_brl, bool) or not isinstance(transaction_costs_brl, (int, float)) or not math.isfinite(transaction_costs_brl) or transaction_costs_brl < 0):
        raise ValueError("transaction_costs_brl must be a non-negative finite amount")
    option_id = position.ticker.upper()
    underlying = (position.underlying_ticker or "").upper()
    option_type = (position.option_type or "").upper()
    _valid_contract_quote(old_contract, old_quote, option_id=option_id, underlying=underlying,
                          option_type=option_type, strike=position.strike,
                          expiration=position.expiration_date, as_of=as_of)
    is_short = position.quantity < 0
    close = _leg(old_contract, old_quote, trade_side="BUY" if is_short else "SELL", quantity=quantity_units)
    alternatives = [
        {"alternative_id": "KEEP", "label": "Manter posição", "status": "CALCULATED_GROSS",
         "legs": [], "incremental_gross_cash_flow_brl": 0.0,
         "incremental_net_cash_flow_brl": 0.0,
         "transaction_costs_brl": 0.0,
         "accumulated_realized_pnl_brl": None,
         "reason": "Sem operação agora; resultado acumulado depende do histórico de abertura e custos."},
        {"alternative_id": "CLOSE", "label": "Encerrar quantidade selecionada", "status": "CALCULATED_GROSS" if close["gross_incremental_cash_flow_brl"] is not None else "EXECUTABLE_PRICE_UNKNOWN",
         "legs": [close], "incremental_gross_cash_flow_brl": close["gross_incremental_cash_flow_brl"],
         "incremental_net_cash_flow_brl": (close["gross_incremental_cash_flow_brl"] - transaction_costs_brl) if close["gross_incremental_cash_flow_brl"] is not None and transaction_costs_brl is not None else None,
         "transaction_costs_brl": transaction_costs_brl,
         "accumulated_realized_pnl_brl": None,
         "reason": "Fluxo incremental de execução, não lucro acumulado; custos de abertura/fechamento ausentes."},
    ]
    if new_contract is None or new_quote is None:
        raise ValueError("Select one explicit roll destination contract before comparing all three alternatives")
    new_id = new_contract.option_id.upper()
    _valid_contract_quote(new_contract, new_quote, option_id=new_id, underlying=underlying,
                          option_type=option_type, strike=None, expiration=new_contract.expiration_date,
                          as_of=as_of)
    if new_contract.expiration_date <= old_contract.expiration_date:
        raise ValueError("Roll destination must expire after the current contract")
    open_leg = _leg(new_contract, new_quote, trade_side="SELL" if is_short else "BUY", quantity=quantity_units)
    roll_flow = None if close["gross_incremental_cash_flow_brl"] is None or open_leg["gross_incremental_cash_flow_brl"] is None else round(close["gross_incremental_cash_flow_brl"] + open_leg["gross_incremental_cash_flow_brl"], 8)
    alternatives.append({"alternative_id": "ROLL", "label": "Rolar para o contrato selecionado", "status": "CALCULATED_GROSS" if roll_flow is not None else "EXECUTABLE_PRICE_UNKNOWN",
                         "legs": [close, open_leg], "incremental_gross_cash_flow_brl": roll_flow,
                         "incremental_net_cash_flow_brl": roll_flow - transaction_costs_brl if roll_flow is not None and transaction_costs_brl is not None else None,
                         "transaction_costs_brl": transaction_costs_brl,
                         "accumulated_realized_pnl_brl": None,
                         "reason": "Crédito/débito combinado dos dois negócios; fluxo de rolagem não é lucro."})
    selected_positions = []
    for item in portfolio.positions:
        row = {"position_id": item.position_id, "ticker": item.ticker, "instrument_type": item.instrument_type, "quantity": item.quantity,
               "underlying_ticker": item.underlying_ticker, "option_type": item.option_type, "strike": item.strike,
               "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
               "source_ref": item.source_ref, "treatment": "PRESERVED"}
        if item.position_id == position.position_id:
            remaining = abs(position.quantity) - quantity_units
            if remaining:
                selected_positions.append({**row, "quantity": -remaining if is_short else remaining, "treatment": "REMAINING_AFTER_SELECTED_ACTION"})
        else:
            selected_positions.append(row)
    roll_positions = list(selected_positions)
    roll_positions.append({"position_id": f"roll:{new_id}", "ticker": new_id, "instrument_type": "OPTION",
                           "quantity": -quantity_units if is_short else quantity_units,
                           "underlying_ticker": underlying, "option_type": option_type,
                           "strike": new_contract.strike, "expiration_date": new_contract.expiration_date.isoformat(),
                           "source_ref": new_quote.source_record_id or new_quote.source, "treatment": "PROPOSED_ROLL_LEG"})
    close_cash_after = (portfolio.cash + close["gross_incremental_cash_flow_brl"] - transaction_costs_brl
                        if portfolio.cash_is_known and close["gross_incremental_cash_flow_brl"] is not None and transaction_costs_brl is not None else None)
    roll_cash_after = (portfolio.cash + roll_flow - transaction_costs_brl
                       if portfolio.cash_is_known and roll_flow is not None and transaction_costs_brl is not None else None)
    return {"policy_version": _POLICY, "as_of": as_of.isoformat(), "portfolio_revision": portfolio_revision,
            "position": {"option_id": option_id, "side": "SHORT" if is_short else "LONG",
                         "position_quantity_units": abs(position.quantity), "selected_quantity_units": quantity_units,
                         "snapshot_as_of": portfolio.as_of.isoformat(), "source_ref": position.source_ref},
            "alternatives": alternatives,
            "portfolio_before": {"snapshot_as_of": portfolio.as_of.isoformat(), "positions": [
                {"position_id": p.position_id, "ticker": p.ticker, "instrument_type": p.instrument_type, "quantity": p.quantity,
                 "underlying_ticker": p.underlying_ticker, "option_type": p.option_type, "strike": p.strike,
                 "expiration_date": p.expiration_date.isoformat() if p.expiration_date else None, "source_ref": p.source_ref}
                for p in portfolio.positions], "cash_brl": portfolio.cash if portfolio.cash_is_known else None,
                "cash_status": "KNOWN" if portfolio.cash_is_known else "UNKNOWN"},
            "portfolio_after_keep": {"positions": [
                {"position_id": p.position_id, "ticker": p.ticker, "instrument_type": p.instrument_type, "quantity": p.quantity,
                 "underlying_ticker": p.underlying_ticker, "option_type": p.option_type, "strike": p.strike,
                 "expiration_date": p.expiration_date.isoformat() if p.expiration_date else None, "source_ref": p.source_ref,
                 "treatment": "UNCHANGED"} for p in portfolio.positions],
                "cash_brl": portfolio.cash if portfolio.cash_is_known else None,
                "cash_status": "PRESERVED" if portfolio.cash_is_known else "UNKNOWN"},
            "portfolio_after_close": {"positions": selected_positions, "cash_change_gross_brl": alternatives[1]["incremental_gross_cash_flow_brl"],
                                      "cash_after_brl": close_cash_after, "cash_status": "CALCULATED_AFTER_EXPLICIT_COSTS" if close_cash_after is not None else "UNKNOWN_COSTS_OR_CASH_BASIS"},
            "portfolio_after_roll": {"positions": roll_positions, "cash_change_gross_brl": roll_flow,
                                     "cash_after_brl": roll_cash_after, "cash_status": "CALCULATED_AFTER_EXPLICIT_COSTS" if roll_cash_after is not None else "UNKNOWN_COSTS_OR_CASH_BASIS"},
            "summary": "Comparação determinística de manter, encerrar e rolar. Valores mostram fluxo bruto incremental; custos, caixa final e lucro acumulado permanecem desconhecidos sem as respectivas fontes.",
            "comparison": {"ranking": "NOT_APPLIED", "preference": None,
                           "reason": "Alternativas têm exposições e prazos distintos; sem horizonte e cenário comum, não há ranking econômico."},
            "limitations": ["Fluxos usam ask para compras e bid para vendas, sem custos ou slippage salvo entrada explícita.",
                            "O fluxo de caixa não equivale a lucro realizado nem resultado acumulado.",
                            "Multiplicador e identidade vêm do snapshot OPLAB atual; confirmar regras e execução com a corretora.",
                            "Caixa total, obrigações e cobertura de todas as posições permanecem UNKNOWN até reconciliar a carteira completa.",
                            "Sem cenário terminal explícito, alternativas com vencimentos distintos não têm payoff comum."],
            "source_refs": list(dict.fromkeys([position.source_ref, old_quote.source, new_quote.source]))}


def management_selection_from_turns(request: OrchestratorRequest) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover only the exact old position ID and chosen size from the latest turn."""
    turns = request.context.get("lab_conversation") or []
    for turn in reversed(turns):
        if not isinstance(turn, dict) or not isinstance(turn.get("response"), dict):
            continue
        result = turn["response"]
        selection = result.get("lab_position_selection")
        if isinstance(selection, dict) and selection.get("status") == "POSITION_AND_QUANTITY_IDENTIFIED":
            intent = management_intent(request)
            return (selection, intent) if intent else None
    return None
