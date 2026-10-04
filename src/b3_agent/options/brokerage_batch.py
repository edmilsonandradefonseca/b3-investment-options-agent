from __future__ import annotations

import hashlib
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from b3_agent.options.brokerage_notes import BrokerageNoteParser
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.transaction import TransactionRepository
from b3_agent.storage.sqlite import SQLiteStore
from b3_agent.repositories.source_manifest import (
    SourceManifestRecord,
    SourceManifestRepository,
)


MAX_BATCH_PDFS = 250
MAX_BATCH_UNCOMPRESSED_BYTES = 100 * 1024 * 1024


class BrokerageBatchIngestionError(ValueError):
    """Raised when a brokerage-note ZIP cannot be processed safely."""


class BrokerageBatchIngestionService:
    """Disk-backed sequential ingestion for brokerage-note PDF batches."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.import_dir = self.data_dir / "imports" / "brokerage_notes"
        self.import_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = OptionTransactionLedger(self.data_dir / "options.sqlite3")
        self.manifest = SourceManifestRepository(
            self.data_dir / "source_manifest.sqlite3"
        )

    @staticmethod
    def _fingerprint(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _ingest_pdf_path(self, path: Path, source_name: str) -> dict[str, object]:
        parser = BrokerageNoteParser()
        transactions = parser.parse(path)
        stock_transactions = parser.parse_stocks(path)
        if not transactions and not stock_transactions:
            raise BrokerageBatchIngestionError(
                f"{source_name}: nenhuma operação de ação ou opção encontrada"
            )

        first_source_ref = transactions[0].source_ref if transactions else stock_transactions[0].source_ref
        note_number = (
            transactions[0].note_number if transactions
            else first_source_ref.split(":")[2]
        )
        fingerprint = self._fingerprint(path)
        safe_name = Path(source_name).name
        archived_name = (
            f"{note_number}-{safe_name}" if note_number else f"{fingerprint[:12]}-{safe_name}"
        )
        archived_path = self.import_dir / archived_name
        if not archived_path.exists():
            archived_path.write_bytes(path.read_bytes())

        inserted_options = self.ledger.append(transactions)
        transaction_database = self.data_dir / "b3_agent.db"
        SQLiteStore(transaction_database).initialize()
        inserted_stocks = TransactionRepository(str(transaction_database)).append_many(stock_transactions)
        inserted = inserted_options + inserted_stocks
        trade_dates = [item.as_of for item in transactions if item.as_of is not None]
        trade_dates.extend(item.executed_at.date() for item in stock_transactions)
        all_transactions = (*transactions, *stock_transactions)
        coverage_start = min(trade_dates) if trade_dates else None
        coverage_end = max(trade_dates) if trade_dates else None
        source_ref = first_source_ref.split(f":{safe_name}")[0]

        self.manifest.upsert(
            SourceManifestRecord(
                source_fingerprint=fingerprint,
                source_type="BROKERAGE_NOTE",
                source_id=note_number or fingerprint,
                source_ref=source_ref,
                file_name=safe_name,
                imported_at=datetime.now(timezone.utc),
                record_count=len(all_transactions),
                coverage_start=coverage_start,
                coverage_end=coverage_end,
                scope="PERIOD_ONLY",
                completeness="UNKNOWN",
            )
        )

        return {
            "file": source_name,
            "note_number": note_number,
            "parsed_count": len(all_transactions),
            "inserted_count": inserted,
        }

    def ingest_zip(self, zip_path: str | Path) -> dict[str, object]:
        archive_path = Path(zip_path)
        processed: list[dict[str, object]] = []
        failures: list[dict[str, str]] = []

        try:
            with zipfile.ZipFile(archive_path) as archive:
                members = [
                    item
                    for item in archive.infolist()
                    if not item.is_dir() and item.filename.lower().endswith(".pdf")
                ]
                if not members:
                    raise BrokerageBatchIngestionError("ZIP não contém arquivos PDF")
                if len(members) > MAX_BATCH_PDFS:
                    raise BrokerageBatchIngestionError(
                        f"ZIP contém {len(members)} PDFs; limite é {MAX_BATCH_PDFS}"
                    )

                total_uncompressed = sum(item.file_size for item in members)
                if total_uncompressed > MAX_BATCH_UNCOMPRESSED_BYTES:
                    raise BrokerageBatchIngestionError(
                        "ZIP excede 100 MB descompactados"
                    )

                for item in members:
                    suffix = Path(item.filename).suffix or ".pdf"
                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=suffix,
                        dir=self.import_dir,
                    ) as handle:
                        temp_path = Path(handle.name)
                        with archive.open(item) as source:
                            while True:
                                chunk = source.read(1024 * 1024)
                                if not chunk:
                                    break
                                handle.write(chunk)

                    try:
                        processed.append(
                            self._ingest_pdf_path(temp_path, item.filename)
                        )
                    except Exception as exc:
                        failures.append(
                            {"file": item.filename, "error": str(exc)}
                        )
                    finally:
                        temp_path.unlink(missing_ok=True)
        except zipfile.BadZipFile as exc:
            raise BrokerageBatchIngestionError("arquivo ZIP inválido") from exc

        return {
            "status": "processed",
            "files_total": len(processed) + len(failures),
            "files_processed": len(processed),
            "files_failed": len(failures),
            "parsed_count": sum(int(item["parsed_count"]) for item in processed),
            "inserted_count": sum(int(item["inserted_count"]) for item in processed),
            "processed": processed,
            "failures": failures,
        }
