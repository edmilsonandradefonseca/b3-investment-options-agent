from __future__ import annotations

import re
import math
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from b3_agent.schemas.position import PortfolioContext, Position
from b3_agent.schemas.received_income import (
    ReceivedIncomeContext, ReceivedStockIncome, StockIncomeSummary,
)


class PortfolioIngestionError(ValueError):
    """Raised when the authoritative BTG portfolio cannot be parsed."""


def _text(value: object) -> str:
    return "" if value is None else str(value).strip().replace("*", "")


def _number(value: object) -> float | None:
    if value is None or (isinstance(value, str) and value.strip() in {"", "-"}):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PortfolioIngestionError(f"expected numeric value, got {value!r}") from exc


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise PortfolioIngestionError(f"expected date, got {value!r}")


def _find_section(rows: list[tuple[object, ...]], label: str) -> int:
    for index, row in enumerate(rows):
        if any(isinstance(value, str) and label in value for value in row):
            return index
    raise PortfolioIngestionError(f"section not found: {label}")


def _statement_date(workbook) -> date:
    return _statement_period(workbook)[1]


def _statement_period(workbook) -> tuple[date, date]:
    for row in workbook["Capa"].iter_rows(values_only=True):
        for value in row:
            if isinstance(value, str):
                match = re.search(r"Período de (\d{2}/\d{2}/\d{2}) a (\d{2}/\d{2}/\d{2})", value)
                if match:
                    start, end = (datetime.strptime(v, "%d/%m/%y").date() for v in match.groups())
                    if start > end:
                        raise PortfolioIngestionError("statement period is reversed")
                    return start, end
    raise PortfolioIngestionError("statement period end not found")


def _received_income(rows, period_start: date, period_end: date) -> ReceivedIncomeContext | None:
    sections = [i for i, row in enumerate(rows) if "Movimentação > Ações" in row]
    if not sections:
        return None
    if len(sections) != 1:
        raise PortfolioIngestionError("ambiguous stock movement section")
    start = sections[0]
    if start + 1 >= len(rows) or tuple(rows[start + 1][1:9]) != (
        "Data", "Transação", "Código", "Qtde.", "Preço R$", "Valor Bruto R$",
        "Corretagem e Emolumentos R$", "Valor Líquido R$",
    ):
        raise PortfolioIngestionError("unsupported stock movement columns")
    payments = []
    identities = set()
    duplicate_rows_omitted = 0
    for index in range(start + 2, len(rows)):
        row = rows[index]
        if any(isinstance(v, str) and " > " in v for v in row):
            break
        kind = _text(row[2])
        if kind not in {"RECEBIMENTO DIVIDENDOS", "JUROS S/CAPITAL"}:
            continue
        stamp = _as_date(row[1])
        ticker = _text(row[3]).upper()
        if not ticker or not period_start <= stamp <= period_end:
            raise PortfolioIngestionError("invalid stock distribution identity/date")
        quantity, gross, net = (_number(row[i]) for i in (4, 6, 8))
        if any(v is not None and not math.isfinite(v) for v in (quantity, gross, net)):
            raise PortfolioIngestionError("nonfinite stock distribution value")
        identity = (ticker, kind, stamp, quantity, gross, net)
        if identity in identities:
            duplicate_rows_omitted += 1
            continue
        identities.add(identity)
        payments.append(ReceivedStockIncome(
            ticker=ticker, payment_date=stamp,
            payment_type="DIVIDEND" if kind == "RECEBIMENTO DIVIDENDOS" else "JCP",
            quantity=quantity, gross_amount=gross, net_amount=net,
            source_ref=f"BTG:Renda Variavel:Movimentacao Acoes:row:{index + 1}",
        ))
    by_ticker = defaultdict(list)
    for payment in payments:
        by_ticker[payment.ticker].append(payment)

    def net_total(items) -> float | None:
        if any(p.net_amount is None for p in items):
            return None
        return float(sum((Decimal(str(p.net_amount)) for p in items), Decimal(0)))

    summaries = tuple(StockIncomeSummary(
        ticker=ticker,
        dividends_net=net_total([p for p in items if p.payment_type == "DIVIDEND"]),
        jcp_net=net_total([p for p in items if p.payment_type == "JCP"]),
        total_net=net_total(items), payment_count=len(items),
    ) for ticker, items in sorted(by_ticker.items()))
    return ReceivedIncomeContext(
        period_start, period_end, tuple(payments), summaries,
        duplicate_rows_omitted=duplicate_rows_omitted,
    )


class BtgRendaVariavelLoader:
    """Load current positions from BTG's authoritative `Renda Variavel` sheet."""

    def load(self, path: str | Path) -> PortfolioContext:
        workbook = load_workbook(Path(path), data_only=True, read_only=True)
        try:
            if "Renda Variavel" not in workbook.sheetnames:
                raise PortfolioIngestionError("Renda Variavel sheet not found")
            rows = list(workbook["Renda Variavel"].iter_rows(values_only=True))
            period_start, as_of = _statement_period(workbook)
            received_income = _received_income(rows, period_start, as_of)
            positions: list[Position] = []

            actions_start = _find_section(rows, "Posição > Ações")
            for row in rows[actions_start + 2 :]:
                ticker = _text(row[1])
                if ticker.startswith("Total em Ações"):
                    break
                if not ticker or ticker in {"Código", "Posição"} or _number(row[3]) in (None, 0):
                    continue
                positions.append(Position(
                    position_id=f"btg:renda-variavel:{ticker}", ticker=ticker,
                    instrument_type="STOCK", quantity=_number(row[3]),
                    average_cost=_number(row[5]), market_price=_number(row[4]),
                    market_value=_number(row[6]), source_ref="BTG:Renda Variavel:Acoes",
                ))

            options_start = _find_section(rows, "Posição > Opções")
            for row in rows[options_start + 2 :]:
                ticker = _text(row[1])
                if ticker.startswith("Total em Opções"):
                    break
                if not ticker or ticker == "Código" or _number(row[3]) in (None, 0):
                    continue
                option_type = _text(row[6]).upper()
                if option_type not in {"PUT", "CALL"}:
                    raise PortfolioIngestionError(f"unsupported option type {row[6]!r} for {ticker}")
                positions.append(Position(
                    position_id=f"btg:renda-variavel:{ticker}", ticker=ticker,
                    instrument_type="OPTION", quantity=_number(row[3]),
                    strike=_number(row[4]), expiration_date=_as_date(row[5]),
                    option_type=option_type, underlying_ticker=_text(row[2]),
                    contract_multiplier=1.0, market_price=_number(row[8]),
                    market_value=_number(row[9]), source_ref="BTG:Renda Variavel:Opcoes",
                ))

            return PortfolioContext(
                as_of=as_of, positions=tuple(positions), cash=0.0, cash_is_known=False,
                source_refs=("BTG:Renda Variavel",) + ((received_income.source_ref,) if received_income else ()), quality_status="VALIDATED",
                received_income=received_income,
            )
        finally:
            workbook.close()
