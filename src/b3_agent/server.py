from __future__ import annotations

from functools import lru_cache
from dataclasses import asdict
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from b3_agent.config import settings
from b3_agent.options.transactions import OptionsTransactionLoader
from b3_agent.options.brokerage_notes import BrokerageNoteParser
from b3_agent.options.brokerage_batch import (
    BrokerageBatchIngestionError,
    BrokerageBatchIngestionService,
)
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.transaction import TransactionRepository
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.source_manifest import SourceManifestRecord, SourceManifestRepository
from b3_agent.schemas.transaction import Transaction
from b3_agent.storage.sqlite import SQLiteStore
from b3_agent.orchestration import OrchestratorRequest, OrchestratorResponse, b3_orchestrator, configure_default_workflow
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.research_events import ResearchEventService
from b3_agent.runtime import RuntimeManager


class OrchestrateRequest(BaseModel):
    """Transport contract for clients of the B3 Orchestrator Server."""

    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1)
    ticker: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class TransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    instrument_type: str
    ticker: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    price: float = Field(ge=0)
    executed_at: datetime | None = None
    broker: str = ""


class TransactionResponse(BaseModel):
    transaction_id: str
    executed_at: datetime
    action: str
    instrument_type: str
    ticker: str
    quantity: float
    price: float
    broker: str
    source_ref: str


class OrchestrateResponse(BaseModel):
    """JSON-safe transport representation of the logical orchestrator response."""

    status: str
    result: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    audit: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


app = FastAPI(
    title="B3 Orchestrator Server",
    version="0.1.0",
    description="API gateway/runtime boundary for the B3 Investment Intelligence workflow.",
)

# The desktop shell is a local Tauri webview. Keep CORS narrowly scoped to
# local development and the Tauri production origins; investment logic stays
# entirely behind the orchestrator.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://tauri.localhost",
        "tauri://localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@lru_cache(maxsize=1)
def _configure_runtime() -> None:
    """Compose the production workflow once, on first orchestration request."""
    configure_default_workflow()


def _transaction_repository() -> TransactionRepository:
    database = settings.data_dir / "b3_agent.db"
    SQLiteStore(database).initialize()
    return TransactionRepository(str(database))


def _transaction_response(item: Transaction) -> TransactionResponse:
    return TransactionResponse(
        transaction_id=item.transaction_id,
        executed_at=item.executed_at,
        action=item.action,
        instrument_type=item.instrument_type,
        ticker=item.ticker,
        quantity=item.quantity,
        price=item.price,
        broker=item.broker,
        source_ref=item.source_ref,
    )


@app.post("/transactions", response_model=TransactionResponse, status_code=201)
def add_transaction(request: TransactionRequest) -> TransactionResponse:
    executed_at = request.executed_at or datetime.now(timezone.utc)
    if executed_at.tzinfo is None:
        raise HTTPException(status_code=400, detail="executed_at must be timezone-aware")
    try:
        transaction = Transaction(
            transaction_id=f"tx:{uuid4()}",
            executed_at=executed_at,
            action=request.action.upper().strip(),
            instrument_type=request.instrument_type.upper().strip(),
            ticker=request.ticker.upper().strip(),
            quantity=request.quantity,
            price=request.price,
            broker=request.broker,
        )
        return _transaction_response(_transaction_repository().add(transaction))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/transactions", response_model=list[TransactionResponse])
def list_transactions(limit: int = 100) -> list[TransactionResponse]:
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return [_transaction_response(item) for item in _transaction_repository().list(limit)]



def _import_dir() -> Path:
    path = settings.data_dir / "imports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _replace_validated_upload(upload: UploadFile, filename: str, validator) -> dict[str, Any]:
    """Validate a workbook completely, then atomically replace the active snapshot."""
    if not upload.filename or not upload.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="arquivo deve ser Excel (.xlsx ou .xlsm)")

    target = _import_dir() / filename
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            prefix=f".{filename}.",
            suffix=Path(upload.filename).suffix.lower(),
            dir=_import_dir(),
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        validator(temp_path)
        temp_path.replace(target)
        return {
            "status": "replaced",
            "file": upload.filename,
            "active_file": str(target),
            "message": "snapshot anterior substituído; dados não são acumulativos",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel inválido: {exc}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
    

@app.post("/imports/portfolio")
def import_portfolio(file: UploadFile = File(...)) -> dict[str, Any]:
    """Replace the authoritative BTG portfolio snapshot after validation."""
    result = _replace_validated_upload(
        file,
        "portfolio.xlsx",
        lambda path: BtgRendaVariavelLoader().load(path),
    )
    _configure_runtime.cache_clear()
    return result


@app.get("/portfolio/current")
def current_portfolio() -> dict[str, Any]:
    """Read the validated BTG snapshot without recomputing market facts."""
    path = _import_dir() / "portfolio.xlsx"
    if not path.exists():
        return {"status": "NOT_AVAILABLE", "as_of": None, "updated_at": None, "positions": []}
    try:
        context = BtgRendaVariavelLoader().load(path)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"snapshot indisponível: {exc}") from exc
    return {
        "status": context.quality_status,
        "as_of": context.as_of.isoformat(),
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "source_refs": list(context.source_refs),
        "positions": [asdict(position) for position in context.positions],
    }


class CapitalProfileRequest(BaseModel):
    available_capital: float = Field(ge=0)
    minimum_reserve: float = Field(ge=0)


def _capital_connection() -> sqlite3.Connection:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.data_dir / "capital_profile.sqlite3")
    connection.execute("CREATE TABLE IF NOT EXISTS capital_profile (account TEXT PRIMARY KEY, available REAL NOT NULL, reserve REAL NOT NULL, updated_at TEXT NOT NULL)")
    return connection


@app.get("/capital-profile")
def get_capital_profile() -> dict[str, Any]:
    with _capital_connection() as connection:
        row = connection.execute("SELECT available, reserve, updated_at FROM capital_profile WHERE account = ?", ("BTG",)).fetchone()
    if row is None:
        return {"status": "NOT_AVAILABLE", "account": "BTG", "available_capital": None, "minimum_reserve": None, "usable_capital": None, "updated_at": None}
    return {"status": "manual", "account": "BTG", "available_capital": row[0], "minimum_reserve": row[1], "usable_capital": row[0] - row[1], "updated_at": row[2]}


@app.post("/capital-profile")
def save_capital_profile(request: CapitalProfileRequest) -> dict[str, Any]:
    if request.minimum_reserve > request.available_capital:
        raise HTTPException(status_code=400, detail="reserva mínima excede capital disponível")
    with _capital_connection() as connection:
        connection.execute("INSERT INTO capital_profile VALUES (?, ?, ?, ?) ON CONFLICT(account) DO UPDATE SET available=excluded.available, reserve=excluded.reserve, updated_at=excluded.updated_at", ("BTG", request.available_capital, request.minimum_reserve, datetime.now(timezone.utc).isoformat()))
    return get_capital_profile()


@app.post("/imports/options")
def import_options(file: UploadFile = File(...)) -> dict[str, Any]:
    """Replace the options transactions snapshot after validation."""
    result = _replace_validated_upload(
        file,
        "options_transactions.xlsx",
        lambda path: OptionsTransactionLoader().load(path),
    )
    _configure_runtime.cache_clear()
    return result


def _store_brokerage_note(upload: UploadFile) -> dict[str, Any]:
    """Validate, archive and persist a brokerage-note PDF."""
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="nota de corretagem deve ser PDF (.pdf)")

    notes_dir = _import_dir() / "brokerage_notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(upload.filename).name
    target = notes_dir / safe_name
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            prefix=f".{safe_name}.",
            suffix=".pdf",
            dir=notes_dir,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        if temp_path.stat().st_size < 5:
            raise ValueError("PDF vazio ou inválido")

        transactions = BrokerageNoteParser().parse(temp_path)
        source_fingerprint = hashlib.sha256(temp_path.read_bytes()).hexdigest()
        temp_path.replace(target)

        ledger_path = settings.data_dir / "options.sqlite3"
        inserted_count = OptionTransactionLedger(ledger_path).append(transactions)

        note_number = transactions[0].note_number
        source_ref = transactions[0].source_ref.split(f":{safe_name}")[0]
        trade_dates = [item.as_of for item in transactions if item.as_of is not None]
        coverage_start = min(trade_dates) if trade_dates else None
        coverage_end = max(trade_dates) if trade_dates else None

        SourceManifestRepository(settings.data_dir / "source_manifest.sqlite3").upsert(
            SourceManifestRecord(
                source_fingerprint=source_fingerprint,
                source_type="BROKERAGE_NOTE",
                source_id=note_number or source_fingerprint,
                source_ref=source_ref,
                file_name=safe_name,
                imported_at=datetime.now(timezone.utc),
                record_count=len(transactions),
                coverage_start=coverage_start,
                coverage_end=coverage_end,
                scope="PERIOD_ONLY",
                completeness="UNKNOWN",
            )
        )

        return {
            "status": "processed",
            "file": upload.filename,
            "active_file": str(target),
            "note_number": note_number,
            "trade_date": (
                coverage_start.isoformat()
                if coverage_start == coverage_end and coverage_start
                else None
            ),
            "parsed_count": len(transactions),
            "inserted_count": inserted_count,
            "transaction_ids": [item.transaction_id for item in transactions],
            "message": "nota de corretagem processada e registrada no ledger",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"nota de corretagem inválida: {exc}",
        ) from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.post("/imports/brokerage-notes")
def import_brokerage_note(file: UploadFile = File(...)) -> dict[str, Any]:
    """Append option trades from a brokerage note to the historical ledger."""
    result = _store_brokerage_note(file)
    _configure_runtime.cache_clear()
    return result


@app.post("/imports/brokerage-notes/batch")
def import_brokerage_note_batch(file: UploadFile = File(...)) -> dict[str, Any]:
    """Process a ZIP of brokerage-note PDFs sequentially from disk."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="lote deve ser ZIP (.zip)")

    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            prefix=".brokerage-batch.",
            suffix=".zip",
            dir=_import_dir(),
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        result = BrokerageBatchIngestionService(settings.data_dir).ingest_zip(
            temp_path
        )
        _configure_runtime.cache_clear()
        return result
    except BrokerageBatchIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"lote de notas inválido: {exc}",
        ) from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.get("/imports/brokerage-notes/upload", response_class=HTMLResponse)
def brokerage_note_batch_upload_page() -> HTMLResponse:
    """Minimal direct-to-FastAPI upload page for large brokerage-note batches."""
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="pt-BR">
          <head>
            <meta charset="utf-8">
            <title>B3 Brokerage Notes Batch Import</title>
          </head>
          <body style="font-family: sans-serif; max-width: 720px; margin: 40px auto;">
            <h2>B3 — Importar ZIP de notas de corretagem</h2>
            <p>
              O arquivo é enviado diretamente ao backend B3 e processado
              sequencialmente em disco. O ZIP não passa pela sessão do Streamlit.
            </p>
            <form method="post" action="/imports/brokerage-notes/batch"
                  enctype="multipart/form-data">
              <input type="file" name="file" accept=".zip,application/zip" required>
              <button type="submit">Importar ZIP</button>
            </form>
          </body>
        </html>
        """
    )


def _response_to_model(response: OrchestratorResponse) -> OrchestrateResponse:
    return OrchestrateResponse(
        status=response.status,
        result=response.result,
        sources=list(response.sources),
        audit=list(response.audit),
        error=response.error,
    )


@app.get("/health")
def health() -> dict[str, Any]:
    """Return application/configuration health without mutating shared services."""
    return {
        "status": "ok",
        "service": "b3-orchestrator-server",
        "workflow_configured": _configure_runtime.cache_info().currsize > 0,
        "llm_enabled": settings.llm_enabled,
        "runtime": {
            "embedding_url": os.getenv("B3_EMBEDDING_URL", "http://127.0.0.1:8093"),
            "qdrant_url": os.getenv("B3_QDRANT_URL", "http://127.0.0.1:6333"),
            "neo4j_uri": os.getenv("B3_NEO4J_URI", "bolt://127.0.0.1:7687"),
            "qdrant_collection": "b3_evidence_768_hybrid",
            "oplab_token_configured": bool(os.getenv("OPLAB_API_TOKEN")),
        },
    }


@app.get("/runtime/status")
def runtime_status() -> dict[str, Any]:
    """Expose the operational runtime state through the Orchestrator."""
    return RuntimeManager().status(health_override="ok")


@app.get("/analysis/live/{ticker}")
def live_analysis(ticker: str) -> dict[str, Any]:
    """Return normalized live market/options analytics for one B3 underlying."""
    try:
        snapshot = LiveProviderService().load(ticker)
        latest = max(
            snapshot.market_records,
            key=lambda item: item.observation_timestamp,
        )
        return {
            "ticker": snapshot.ticker,
            "as_of": snapshot.as_of.isoformat(),
            "source_refs": list(snapshot.source_refs),
            "market": {
                "history_count": len(snapshot.market_records),
                "latest": asdict(latest),
            },
            "options": {
                "contract_count": len(snapshot.option_contracts),
                "quote_count": len(snapshot.option_quotes),
                "contracts": [asdict(item) for item in snapshot.option_contracts],
                "quotes": [asdict(item) for item in snapshot.option_quotes],
                "analysis": asdict(snapshot.options_analysis),
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/research/news/{ticker}")
def research_news(ticker: str, limit: int = 20) -> dict[str, Any]:
    """Acquire live web/news evidence and normalize it through UC-10 PIT rules."""
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try:
        as_of = datetime.now(timezone.utc)
        records = SearxngNewsAdapter(
            base_url=os.getenv("B3_SEARXNG_URL", "http://127.0.0.1:8080")
        ).search(ticker, limit=limit)
        snapshot = ResearchEventService().build(records, as_of=as_of)
        return {
            "ticker": ticker.upper().strip(),
            "as_of": snapshot.as_of.isoformat(),
            "excluded_future_count": snapshot.excluded_future_count,
            "source_refs": list(snapshot.source_refs),
            "events": [asdict(item) for item in snapshot.events],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/version")
def version() -> dict[str, str]:
    return {"service": "b3-orchestrator-server", "version": app.version}


@app.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """Translate HTTP input to the transport-agnostic ``b3_orchestrator`` contract."""
    try:
        normalized = OrchestratorRequest.from_inputs(
            task=request.task,
            ticker=request.ticker,
            context=request.context,
        )
        _configure_runtime()
        response = b3_orchestrator(
            task=normalized.task,
            ticker=normalized.ticker,
            context=normalized.context,
        )
        return _response_to_model(response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


__all__ = ["OrchestrateRequest", "OrchestrateResponse", "app"]
