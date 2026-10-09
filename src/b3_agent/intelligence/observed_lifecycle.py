"""Derived execution movements, never canonical outcomes or a new ledger."""
from dataclasses import asdict, dataclass
from decimal import Decimal

from b3_agent.schemas.operation import Operation


@dataclass(frozen=True)
class ObservedLifecycle:
    operation_id: str
    symbol: str
    broker: str
    instrument_type: str
    identity_match: str
    first_trade_date: str
    last_trade_date: str
    status: str
    observed_direction: str
    observed_quantity_delta: float
    partial_reduction_count: int
    gross_execution_cash_flow: float
    source_transaction_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    movements: tuple[dict, ...]
    movement_details_omitted: int
    source_transaction_details_omitted: int
    opening_balance_assumption: str = "ZERO_UNVERIFIED"
    economic_outcome_status: str = "UNKNOWN"
    current_position_quantity: float | None = None
    realized_pnl: float | None = None
    assigned: bool | None = None
    exercised: bool | None = None
    expired_otm: bool | None = None
    roll_chain_result: float | None = None
    eligible_for_learning: bool = False


def project_observed_lifecycle(operation: Operation, rows: list[dict]) -> dict:
    """Use already ordered, broker-isolated rows admitted by PersonalHistoryService.

    Quantity movements assume an unverified zero opening balance. They describe
    this sequence only and must never be used as current holdings, finalized
    profit, repurchase of a proven short, assignment or a roll link.
    """
    balance = Decimal(0)
    cash = Decimal(0)
    movements = []
    partial_reductions = 0
    for row in rows:
        delta = Decimal(str(row["quantity"])) * (1 if row["side"] == "BUY" else -1)
        after = balance + delta
        if balance == 0:
            kind = "INITIAL_DELTA_UNVERIFIED"
        elif after == 0:
            kind = "OBSERVED_NET_FLAT"
        elif abs(after) < abs(balance):
            kind = "OBSERVED_PARTIAL_REDUCTION"
            partial_reductions += 1
        else:
            kind = "OBSERVED_INCREASE"
        movements.append({
            "transaction_id": row["transaction_id"], "trade_date": row["trade_date"],
            "date_precision": row["date_precision"], "side": row["side"],
            "quantity": row["quantity"], "movement": kind,
            "observed_delta_before": float(balance), "observed_delta_after": float(after),
            "cash_flow": row["cash_flow"], "source_ref": row["source_ref"],
        })
        cash += Decimal(str(row["cash_flow"]))
        balance = after
    first, last = rows[0], rows[-1]
    return asdict(ObservedLifecycle(
        operation_id=operation.operation_id, symbol=first["symbol"], broker=first["broker"],
        instrument_type=first["instrument_type"], identity_match=first["identity_match"],
        first_trade_date=first["trade_date"], last_trade_date=last["trade_date"],
        status="OBSERVED_NET_FLAT_SEQUENCE" if balance == 0 else "OBSERVED_OUTSTANDING_DELTA",
        observed_direction=operation.direction.value, observed_quantity_delta=float(balance),
        partial_reduction_count=partial_reductions, gross_execution_cash_flow=float(cash),
        source_transaction_ids=operation.source_transaction_ids[-20:],
        source_transaction_details_omitted=max(0, len(operation.source_transaction_ids)-20),
        source_refs=tuple(dict.fromkeys(r["source_ref"] for r in rows[-20:] if r["source_ref"])),
        movements=tuple(movements[-20:]), movement_details_omitted=max(0, len(movements)-20),
    ))


def historical_admission_context(sequences: list[dict]) -> dict:
    """Explicit PRE-ANALYSIS boundary: observations cannot train/rank outcomes."""
    return {
        "policy_version": "personal-history-admission-v1",
        "status": "OBSERVATIONS_ONLY" if sequences else "NO_ADMISSIBLE_SEQUENCES",
        "scope": "PERSONAL_EXECUTION_OBSERVATIONS",
        "observed_sequence_count": len(sequences),
        "unknown_outcome_count": len(sequences),
        "eligible_outcome_count": 0,
        "similarity_confidence": None,
        "supporting_learning_ids": [], "contradicting_learning_ids": [],
        "ranking_effect": "NONE",
        "required_evidence": {
            "UC-07": ["ACCOUNT_COVERAGE_AND_OPENING_BALANCE", "CONTRACT_IDENTITY_AND_PIT_COVERAGE", "TERMINAL_SETTLEMENT_OR_LINKED_ROLL_EVIDENCE"],
            "UC-08": ["CANONICAL_FINAL_OUTCOME", "PIT_ENTRY_SNAPSHOT_AND_REGIME", "CANONICAL_COMMIT_AND_IDEMPOTENT_OUTCOME_EVENT"],
            "UC-09": ["PIT_CURRENT_AND_HISTORICAL_FEATURES", "ELIGIBLE_COMPARABLE_OUTCOMES", "VALIDATED_LEARNING_VERSIONS_AND_CONTRADICTIONS"],
        },
        "limitations": [
            "Zero eligible outcomes means no validated sample, not zero losses or assignments.",
            "Observed deltas assume an unverified zero opening balance; they are not current positions.",
            "Missing outcomes and entry features cannot produce comparable-strategy success rates or a winner.",
            "Personal selection bias applies; no observation is a market assignment probability.",
        ],
    }
