from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from b3_agent.schemas.option_transaction import OptionTransaction


class BrokerageNoteIngestionError(ValueError):
    """Raised when a brokerage note cannot be parsed safely."""


_TRADE_RE = re.compile(
    r"^\s*\S+\s+(?P<side>[CV])\s+OPCAO\s+DE\s+"
    r"(?P<option_type>COMPRA|VENDA)\s+\S+\s+"
    r"(?P<ticker>[A-Z0-9]+)\s+(?:ON|PN)\s+"
    r"(?P<quantity>[\d.]+)\s+(?P<price>[\d.,]+)\s+"
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

        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            match = _TRADE_RE.match(line)
            if not match:
                continue

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
                )
            )

        if not transactions:
            raise BrokerageNoteIngestionError(
                f"no option trades found in brokerage note {note_number}"
            )

        return tuple(transactions)
