from __future__ import annotations

from functools import lru_cache
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from b3_agent.config import settings
from b3_agent.options.transactions import OptionsTransactionLoader
from b3_agent.options.brokerage_notes import BrokerageNoteIngestionError, BrokerageNoteParser
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.transaction import TransactionRepository
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.source_manifest import SourceManifestRecord, SourceManifestRepository
from b3_agent.schemas.transaction import Transaction
from b3_agent.storage.sqlite import SQLiteStore
from b3_agent.orchestration import OrchestratorRequest, OrchestratorResponse, b3_orchestrator, configure_default_workflow, configure_dashboard_workflow
from b3_agent.knowledge.context import KnowledgeContextBuilder
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.indexer import KnowledgeIndexer
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever


class KnowledgeQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    as_of: datetime | None = None
    rag_top_k: int = Field(default=5, ge=1, le=20)
    graph_top_k: int = Field(default=20, ge=1, le=100)
    neighbor_depth: int = Field(default=1, ge=0, le=2)


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
        "http://127.0.0.1:5173",
        "http://tauri.localhost",
        "tauri://localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@lru_cache(maxsize=1)
def _configure_runtime(*, dashboard: bool = False) -> None:
    """Compose the workflow required by the request type."""
    if dashboard:
        configure_dashboard_workflow()
    else:
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
    """Validate and stage a brokerage-note PDF behind the orchestrator boundary."""
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

        parser = BrokerageNoteParser()
        transactions = parser.parse(temp_path)

        target_bytes = temp_path.read_bytes()
        source_fingerprint = hashlib.sha256(target_bytes).hexdigest()
        temp_path.replace(target)

        ledger = OptionTransactionLedger(_import_dir().parent / "options.sqlite3")
        inserted_count = ledger.append(transactions)

        note_number = transactions[0].note_number
        source_ref = transactions[0].source_ref.split(f":{safe_name}")[0]
        trade_dates = [item.as_of for item in transactions if item.as_of is not None]
        coverage_start = min(trade_dates) if trade_dates else None
        coverage_end = max(trade_dates) if trade_dates else None
        SourceManifestRepository(_import_dir().parent / "source_manifest.sqlite3").upsert(
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
            "trade_date": coverage_start.isoformat() if coverage_start == coverage_end and coverage_start else None,
            "parsed_count": len(transactions),
            "inserted_count": inserted_count,
            "transaction_ids": [item.transaction_id for item in transactions],
            "message": "nota de corretagem processada e registrada no ledger",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"nota de corretagem inválida: {exc}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.post("/imports/brokerage-notes")
def import_brokerage_note(file: UploadFile = File(...)) -> dict[str, Any]:
    """Stage a brokerage-note PDF without bypassing the orchestrator boundary."""
    return _store_brokerage_note(file)


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
    """Return server health without forcing the investment workflow to initialize."""
    return {
        "status": "ok",
        "service": "b3-orchestrator-server",
        "workflow_configured": _configure_runtime.cache_info().currsize > 0,
        "obsidian_configured": settings.obsidian_vault is not None,
        "llm_enabled": settings.llm_enabled,
    }


@app.get("/version")
def version() -> dict[str, str]:
    return {"service": "b3-orchestrator-server", "version": app.version}




def _knowledge_query(request: KnowledgeQueryRequest) -> dict[str, Any]:
    """Run bounded, deterministic Obsidian + KG retrieval for the Knowledge UI."""
    if settings.obsidian_vault is None:
        raise HTTPException(status_code=503, detail="B3_AGENT_OBSIDIAN_VAULT is not configured")
    vault = ObsidianKnowledgeStore(settings.obsidian_vault)
    graph = InMemoryKnowledgeGraphStore()
    index_result = KnowledgeIndexer(vault, graph).index_all()
    context = KnowledgeContextBuilder(ObsidianRetriever(vault), graph).build(
        request.query,
        rag_top_k=request.rag_top_k,
        graph_top_k=request.graph_top_k,
        neighbor_depth=request.neighbor_depth,
        as_of=request.as_of,
    )
    payload = context.as_dict()
    payload["metadata"] = {
        **payload.get("metadata", {}),
        "notes_scanned": index_result.notes_scanned,
        "notes_changed": index_result.notes_changed,
        "notes_unchanged": index_result.notes_unchanged,
        "entities_indexed": index_result.entities_indexed,
        "relations_indexed": index_result.relations_indexed,
    }
    return payload


@app.post("/knowledge/query")
def query_knowledge(request: KnowledgeQueryRequest) -> dict[str, Any]:
    """Return bounded knowledge evidence and graph context without LLM reasoning."""
    try:
        return _knowledge_query(request)
    except HTTPException:
        raise
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """Translate HTTP input to the transport-agnostic ``b3_orchestrator`` contract."""
    try:
        normalized = OrchestratorRequest.from_inputs(
            task=request.task,
            ticker=request.ticker,
            context=request.context,
        )
        dashboard_view = bool(normalized.context.get("dashboard_view"))
        if dashboard_view:
            _configure_runtime(dashboard=True)
        else:
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
