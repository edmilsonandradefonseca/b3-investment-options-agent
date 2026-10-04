from __future__ import annotations

import re
from datetime import datetime, time, timezone
from pathlib import Path

from pypdf import PdfReader

from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.transaction import Transaction


class BrokerageNoteIngestionError(ValueError):
    """Raised when a brokerage note cannot be parsed safely."""


_TRADE_RE = re.compile(
    r"^\s*\S+\s+(?P<side>[CV])\s+OPCAO\s+DE\s+"
    r"(?P<option_type>COMPRA|VENDA)\s+\S+\s+"
    r"(?P<ticker>[A-Z0-9]+)\s+(?:ON|PN)\s+"
    r"(?P<quantity>[\d.]+)\s+(?P<price>[\d.,]+)\s+"
    r"(?P<amount>[\d.,]+)\s+(?P<cash_side>[DC])\s*$"
)

# BTG also emits blank share classes and the D (day trade) observation.
_EXTENDED_TRADE_RE = re.compile(
    r"^\s*\S+\s+(?P<side>[CV])\s+OPCAO\s+DE\s+"
    r"(?P<option_type>COMPRA|VENDA)\s+\S+\s+"
    r"(?P<ticker>[A-Z0-9]+)\s+(?:(?:ON|PN)\s+)?(?:D\s+)?"
    r"(?P<quantity>[\d.]+)\s+(?P<price>[\d.,]+)\s+"
    r"(?P<amount>[\d.,]+)\s+(?P<cash_side>[DC])\s*$"
)

_STOCK_TRADE_RE = re.compile(
    r"^\s*\S+\s+(?P<side>[CV])\s+VISTA\s+"
    r"(?P<ticker>[A-Z0-9]+)(?:\s+(?:ON|PN|UNT|CI|N[0-9]+|NM|ED|DRN|DR3|F|D|#\d+))*\s+"
    r"(?:D\s+)?(?P<quantity>[\d.]+)\s+(?P<price>[\d.,]+)\s+"
    r"(?P<amount>[\d.,]+)\s+(?P<cash_side>[DC])\s*$"
)

_NOTE_RE = re.compile(r"(?m)^\s*(?P<note>\d{6,})\s*$")
_DATE_RE = re.compile(r"(?m)^\s*(?P<date>\d{2}/\d{2}/\d{4})\s*$")


def _number(value: str) -> float:
    normalized = value.replace(".", "").replace(",", ".")
    return float(normalized)


class BrokerageNoteParser:
    """Parse BTG/Necton brokerage-note PDFs into OptionTransaction records."""

    def parse(self, path: str | Path) -> tuple[OptionTransaction, ...]:
        pdf_path = Path(path)
        if not pdf_path.exists():
            raise BrokerageNoteIngestionError(f"file not found: {pdf_path}")

        try:
            reader = PdfReader(str(pdf_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise BrokerageNoteIngestionError(
                f"unable to extract PDF text: {pdf_path.name}"
            ) from exc

        return self.parse_text(text, source_file=pdf_path.name)

    def parse_text(
        self,
        text: str,
        *,
        source_file: str = "",
    ) -> tuple[OptionTransaction, ...]:
        if not text.strip():
            raise BrokerageNoteIngestionError("brokerage note has no extractable text")

        note_match = _NOTE_RE.search(text)
        date_match = _DATE_RE.search(text)
        if not note_match:
            raise BrokerageNoteIngestionError("brokerage note number not found")
        if not date_match:
            raise BrokerageNoteIngestionError("trade date not found")

        note_number = note_match.group("note")
        trade_date = datetime.strptime(
            date_match.group("date"), "%d/%m/%Y"
        ).date()

        transactions: list[OptionTransaction] = []
        trade_index = 0
        option_row_index = 0

        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            match = _TRADE_RE.match(line)
            legacy_match = match is not None
            match = match or _EXTENDED_TRADE_RE.match(line)
            if not match and "OPCAO DE" in line:
                raise BrokerageNoteIngestionError(
                    f"unsupported option trade row in brokerage note {note_number}; "
                    "note not imported to avoid partial execution history"
                )
            if match is None:
                continue

            option_row_index += 1
            if legacy_match:
                trade_index += 1
            side = match.group("side")
            quantity = _number(match.group("quantity"))
            price = _number(match.group("price"))
            amount = _number(match.group("amount"))

            # Preserve the transaction-side convention used by the XLSX
            # loader: BUY is positive and SELL is negative.
            signed_quantity = quantity if side == "C" else -quantity
            signed_amount = amount if side == "C" else -amount

            ticker = match.group("ticker")
            transaction_id = (
                f"btg-note:{note_number}:{trade_index}:{ticker}"
                if legacy_match else
                f"btg-note:{note_number}:additional:{option_row_index}:{ticker}"
            )
            source_ref = (
                f"BTG:NotaCorretagem:{note_number}"
                + (f":{source_file}" if source_file else "")
            )

            transactions.append(
                OptionTransaction(
                    transaction_id=transaction_id,
                    option_ticker=ticker,
                    broker="BTG Pactual",
                    quantity=signed_quantity,
                    average_cost=price,
                    total_cost=signed_amount,
                    as_of=trade_date,
                    source_ref=source_ref,
                    note_number=note_number,
                    source_type="BROKERAGE_NOTE",
                    source_id=note_number,
                )
            )

        if not transactions and not any(" VISTA " in " ".join(line.split()) for line in text.splitlines()):
            raise BrokerageNoteIngestionError(
                f"no stock or option trades found in brokerage note {note_number}"
            )

        return tuple(transactions)

    def parse_stocks(self, path: str | Path) -> tuple[Transaction, ...]:
        """Parse cash-market share executions from a BTG brokerage-note PDF."""
        pdf_path = Path(path)
        if not pdf_path.exists():
            raise BrokerageNoteIngestionError(f"file not found: {pdf_path}")
        try:
            reader = PdfReader(str(pdf_path))
            text = "\\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise BrokerageNoteIngestionError(
                f"unable to extract PDF text: {pdf_path.name}"
            ) from exc
        return self.parse_stock_text(text, source_file=pdf_path.name)

    def parse_stock_text(
        self, text: str, *, source_file: str = ""
    ) -> tuple[Transaction, ...]:
        """Parse dated VISTA rows, preserving exact ticker, price and quantity."""
        if not text.strip():
            raise BrokerageNoteIngestionError("brokerage note has no extractable text")
        note_match = _NOTE_RE.search(text)
        date_match = _DATE_RE.search(text)
        if not note_match or not date_match:
            raise BrokerageNoteIngestionError("brokerage note number or trade date not found")
        note_number = note_match.group("note")
        trade_date = datetime.strptime(date_match.group("date"), "%d/%m/%Y").date()
        transactions: list[Transaction] = []
        for index, raw_line in enumerate(text.splitlines(), start=1):
            line = " ".join(raw_line.split())
            if " VISTA " not in f" {line} ":
                continue
            match = _STOCK_TRADE_RE.match(line)
            if match is None:
                raise BrokerageNoteIngestionError(
                    f"unsupported cash-market row in brokerage note {note_number}; "
                    "note not imported to avoid partial stock execution history"
                )
            quantity = _number(match.group("quantity"))
            price = _number(match.group("price"))
            side = "BUY" if match.group("side") == "C" else "SELL"
            ticker = match.group("ticker").upper()
            source_ref = (
                f"BTG:NotaCorretagem:{note_number}"
                + (f":{source_file}" if source_file else "")
            )
            transactions.append(Transaction(
                transaction_id=f"btg-note-stock:{note_number}:{index}:{ticker}",
                executed_at=datetime.combine(trade_date, time.min, tzinfo=timezone.utc),
                action=side,
                instrument_type="STOCK",
                ticker=ticker,
                quantity=quantity,
                price=price,
                broker="BTG Pactual",
                source_ref=source_ref,
            ))
        return tuple(transactions)
