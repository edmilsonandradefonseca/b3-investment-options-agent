from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ReceivedStockIncome:
    """Personal cash distribution observed in a broker statement, not an announcement."""

    ticker: str
    payment_date: date
    payment_type: str
    quantity: float | None
    gross_amount: float | None
    net_amount: float | None
    source_ref: str


@dataclass(frozen=True)
class StockIncomeSummary:
    ticker: str
    dividends_net: float | None
    jcp_net: float | None
    total_net: float | None
    payment_count: int


@dataclass(frozen=True)
class ReceivedIncomeContext:
    period_start: date
    period_end: date
    payments: tuple[ReceivedStockIncome, ...]
    summaries: tuple[StockIncomeSummary, ...]
    source_ref: str = "BTG:Renda Variavel:Movimentacao Acoes"
    coverage: str = "STATEMENT_PERIOD_ONLY"
    duplicate_rows_omitted: int = 0
