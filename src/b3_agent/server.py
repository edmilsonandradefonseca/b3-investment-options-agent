from __future__ import annotations

from functools import lru_cache
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
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.transaction import TransactionRepository
from b3_agent.schemas.transaction import Transaction
from b3_agent.storage.sqlite import SQLiteStore
from b3_agent.orchestration import OrchestratorRequest, OrchestratorResponse, b3_orchestrator, configure_default_workflow


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
    return _replace_validated_upload(
        file,
        "portfolio.xlsx",
        lambda path: BtgRendaVariavelLoader().load(path),
    )


@app.post("/imports/options")
def import_options(file: UploadFile = File(...)) -> dict[str, Any]:
    """Replace the options transactions snapshot after validation."""
    return _replace_validated_upload(
        file,
        "options_transactions.xlsx",
        lambda path: OptionsTransactionLoader().load(path),
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
