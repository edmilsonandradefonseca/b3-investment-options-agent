from __future__ import annotations

from functools import lru_cache
from dataclasses import asdict
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4
from typing import Any
from time import monotonic
from b3_agent.intelligence.personal_history import PersonalHistoryService
from b3_agent.intelligence.decision_history import build_decision_history
from b3_agent.intelligence.collection_universe import CollectionUniverseStore

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
from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.repositories.transaction import TransactionRepository
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.source_manifest import SourceManifestRecord, SourceManifestRepository
from b3_agent.schemas.transaction import Transaction
from b3_agent.storage.sqlite import SQLiteStore
from b3_agent.orchestration import OrchestratorRequest, OrchestratorResponse, b3_orchestrator, configure_default_workflow
from b3_agent.orchestration.fast_dispatch import FastRouteDispatcher
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.quant_engine import compute_quant_features
from b3_agent.providers.stock_sources import StockFundamentalsProvider
from b3_agent.providers.brapi.budget import BrapiBudget
from b3_agent.providers.oplab.adapter import OplabAdapter
from b3_agent.providers.oplab.options import OplabOptionsAdapter
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.research_events import ResearchEventService
from b3_agent.runtime import RuntimeManager
from b3_agent.intelligence.observability import (
    local_intelligence_manifests,
    local_intelligence_queues,
    local_intelligence_status,
    local_ticker_intelligence,
)
from b3_agent.routing.decision_intent import explicit_stock_comparison
from b3_agent.intelligence.workspace_context import (
    WorkspaceIntelligenceContextService,
)


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
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://tauri.localhost",
        "tauri://localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@lru_cache(maxsize=1)
def _configure_runtime() -> None:
    """Compose the production workflow once, only when senior reasoning is needed."""
    configure_default_workflow()


_fast_route_dispatcher = FastRouteDispatcher()


def _dispatch_fast_route(request: OrchestratorRequest) -> OrchestratorResponse | None:
    """Return a deterministic V4.1 result or None to escalate to OpenClaw."""
    return _fast_route_dispatcher.dispatch(
        task=request.task,
        ticker=request.ticker,
        context=request.context,
    )


def _workspace_name(request: OrchestratorRequest) -> str:
    return str(
        request.context.get("workspace")
        or request.context.get("dashboard_page")
        or ""
    ).strip()


def _workspace_tickers(request: OrchestratorRequest) -> tuple[str, ...]:
    selected = request.context.get("opportunity_assets")
    if isinstance(selected, (list, tuple)):
        return tuple(dict.fromkeys(str(item).upper().strip() for item in selected))
    values: list[str] = []
    for raw in (
        request.ticker,
        request.context.get("selected_ticker"),
    ):
        if isinstance(raw, str) and raw.strip():
            values.append(raw.upper().strip())

    comparison = request.context.get("comparison_assets")
    if isinstance(comparison, (list, tuple)):
        values.extend(
            str(item).upper().strip()
            for item in comparison
            if str(item).strip()
        )
    values.extend(re.findall(r"(?<![A-Z0-9])([A-Z]{4}\d{1,2})(?![A-Z0-9])", request.task.upper()))
    return tuple(dict.fromkeys(values))


def _dispatch_opportunity_screen(request: OrchestratorRequest) -> OrchestratorResponse | None:
    if _workspace_name(request).casefold() != 'opportunities' or 'opportunity_assets' not in request.context:
        return None
    from b3_agent.opportunity_screen import StockOpportunityScreenService
    assets = request.context['opportunity_assets']
    include = request.context.get('include_portfolio_stocks', False)
    if not isinstance(assets, (list, tuple)) or any(not isinstance(item, str) for item in assets) or not isinstance(include, bool):
        raise ValueError('opportunity_assets must be a list of symbols and include_portfolio_stocks a boolean')
    started = monotonic()
    result = StockOpportunityScreenService().build(assets,
        objective=request.context.get('opportunity_objective', 'COMPARE_ONLY'),
        include_portfolio=include, as_of=request.context.get('as_of'),
        economic_inputs=request.context.get('opportunity_economic_inputs'))
    result['workspace_intelligence'] = {'workspace':'Opportunities', 'as_of':result['as_of'],
        'tickers':result['opportunity_screen']['requested_universe'], 'limitations':result['limitations'], 'derived_intelligence':{}}
    result['derived_synthesis_status'] = 'NOT_REQUESTED'
    result['telemetry'] = {'total_ms':(monotonic()-started)*1000, 'llm_calls':0}
    return OrchestratorResponse(status='COMPLETED', result=result, sources=tuple(result['source_refs']),
        audit=({'event':'observed_stock_screen', 'policy':result['opportunity_screen']['policy_version']},))


def _uses_workspace_intelligence(request: OrchestratorRequest) -> bool:
    return " ".join(_workspace_name(request).casefold().split()) in {
        "opportunities",
        "market intelligence",
        "strategy lab",
    }


def _workspace_intelligence_response(
    request: OrchestratorRequest,
    *,
    deterministic_response: OrchestratorResponse | None,
) -> OrchestratorResponse:
    started = monotonic()
    workspace = _workspace_name(request)
    deterministic_only = request.context.get("analysis_mode") == "deterministic"
    research_mode = request.context.get("research_mode", "stored_first")
    if research_mode not in {"stored_first", "stored_only", "refresh"}:
        raise HTTPException(status_code=422, detail="Invalid research_mode")
    context = WorkspaceIntelligenceContextService().build(
        workspace=workspace,
        tickers=_workspace_tickers(request),
        deterministic_result=(
            deterministic_response.result
            if deterministic_response is not None
            else None
        ),
        include_joao=not deterministic_only,
        research_mode=research_mode,
        **({"history_as_of": request.context["as_of"]} if request.context.get("as_of") is not None else {}),
        **({"history_since": request.context["history_since"]} if request.context.get("history_since") is not None else {}),
        include_joao_perspective=(not deterministic_only and os.getenv("B3_JOAO_SYNC_PERSPECTIVE", "true").lower() == "true"),
    )

    context_payload = context.as_context()
    if deterministic_only:
        facts = context_payload.get("deterministic_context", {})
        workspace_result = facts.get("workspace_result", {})
        market_context = facts.get("market_analysis", {})
        asset_evidence = {
            ticker: entry["asset_evidence"]
            for ticker, entry in market_context.get("tickers", {}).items()
            if isinstance(entry, dict) and isinstance(entry.get("asset_evidence"), dict)
        }
        return OrchestratorResponse(
            status="COMPLETED",
            result={
                **workspace_result,
                **({"asset_evidence": asset_evidence} if asset_evidence else {}),
                **(deterministic_response.result if deterministic_response else {}),
                "workspace_intelligence": {
                    "workspace": workspace,
                    "as_of": facts.get("as_of"),
                    "tickers": list(_workspace_tickers(request)),
                    "market_context": market_context,
                    "derived_intelligence": {},
                    "limitations": list(getattr(context, "limitations", ())),
                    "source_refs": list(context.source_refs),
                },
                "deterministic_context": context_payload.get("deterministic_context", {}),
                "research_context": context_payload.get("deterministic_context", {}).get("market_analysis", {}),
                "stored_research": context_payload.get("deterministic_context", {}).get("stored_research", {}),
        "personal_history": context_payload.get("deterministic_context", {}).get("personal_history", {}),
                "decision_history": context_payload.get("deterministic_context", {}).get("decision_history", {}),
                "canonical_experience_context": {
                    "status": "CANONICAL_LOADER_NOT_CONFIGURED", "learnings": [],
                    "assessment": None, "retrieval": None,
                },
                "derived_synthesis_status": "NOT_REQUESTED",
                "telemetry": {"total_ms": (monotonic()-started)*1000, "llm_calls": 0},
            },
            sources=tuple(dict.fromkeys((*context.source_refs, *(deterministic_response.sources if deterministic_response else ())))),
        )
    senior_context = {
        **request.context,
        **context_payload,
    }
    _configure_runtime()
    senior = b3_orchestrator(
        task=request.task,
        ticker=request.ticker,
        context=senior_context,
    )

    deterministic_result = (
        deterministic_response.result
        if deterministic_response is not None
        else {}
    )
    deterministic_context_payload = context_payload.get(
        "deterministic_context", {}
    )
    market_context = (
        deterministic_context_payload.get("market_analysis", {})
        if isinstance(deterministic_context_payload, dict)
        else {}
    )
    workspace_result = (
        deterministic_context_payload.get("workspace_result", {})
        if isinstance(deterministic_context_payload, dict)
        else {}
    )
    workspace_asset_evidence: dict[str, Any] = {}
    ticker_context = (
        market_context.get("tickers", {})
        if isinstance(market_context, dict)
        else {}
    )
    if isinstance(ticker_context, dict):
        for ticker, entry in ticker_context.items():
            if not isinstance(entry, dict):
                continue
            pack = entry.get("asset_evidence")
            if isinstance(pack, dict):
                workspace_asset_evidence[str(ticker)] = pack

    merged_result = {
        **senior.result,
        **workspace_result,
        **deterministic_result,
        **(
            {"asset_evidence": workspace_asset_evidence}
            if workspace_asset_evidence
            and "asset_evidence" not in deterministic_result
            else {}
        ),
        "derived_synthesis_status": "FAILED" if senior.error else "COMPLETED",
        "personal_history": context_payload.get("deterministic_context", {}).get("personal_history", {}),
        "research_context": market_context,
        "stored_research": context_payload.get("deterministic_context", {}).get("stored_research", {}),
        "decision_history": context_payload.get("deterministic_context", {}).get("decision_history", {}),
        "canonical_experience_context": senior.result.get("canonical_experience_context", {
            "status": "CANONICAL_LOADER_NOT_CONFIGURED", "learnings": [],
            "assessment": None, "retrieval": None,
        }),
        "telemetry": {"total_ms": (monotonic()-started)*1000, "stages": senior.result.get("stage_telemetry", {})},
        "workspace_intelligence": {
            "workspace": context.workspace,
            "context_telemetry": deterministic_context_payload.get("context_telemetry", {}),
            "as_of": context.as_of.isoformat(),
            "tickers": list(context.tickers),
            "market_context": market_context,
            "derived_intelligence": context.derived_intelligence,
            "limitations": list(context.limitations),
            "source_refs": list(context.source_refs),
        },
    }
    sources = tuple(
        dict.fromkeys(
            (
                *(
                    deterministic_response.sources
                    if deterministic_response is not None
                    else ()
                ),
                *context.source_refs,
                *senior.sources,
            )
        )
    )
    audit = tuple(
        [
            *(
                deterministic_response.audit
                if deterministic_response is not None
                else ()
            ),
            {
                "event": "workspace_intelligence_composed",
                "workspace": workspace,
                "tickers": list(context.tickers),
                "joao_status": (
                    context.derived_intelligence.get(
                        "joao_resolve", {}
                    ).get("status")
                ),
            },
            *senior.audit,
        ]
    )
    return OrchestratorResponse(
        status=senior.status,
        result=merged_result,
        sources=sources,
        audit=audit,
        error=senior.error,
    )


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
        "received_income": asdict(context.received_income) if context.received_income is not None else None,
        "intelligence": asdict(PortfolioIntelligenceEngine().build(context)),
    }


@app.get("/history/context")
def personal_history_context(ticker: str | None = None, as_of: datetime | None = None, since: str | None = None):
    """Deterministic read projection; no models, providers, migrations or ingestion."""
    try:
        return PersonalHistoryService(settings.data_dir).build(ticker=ticker, as_of=as_of, since=since)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/intelligence/research-context")
def stored_research_context(ticker: str, as_of: str | None = None, limit: int = 8):
    """Read existing B3 research only; no web search, market fetch or senior model."""
    from b3_agent.intelligence.stored_research import StoredResearchContextService
    try:
        cutoff = datetime.fromisoformat(as_of.replace("Z", "+00:00")) if as_of else datetime.now(timezone.utc)
        return StoredResearchContextService().build(ticker, as_of=cutoff, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/history/decision-context")
def decision_history_context(ticker: str, as_of: datetime | None = None, since: str | None = None):
    """Exact subject evidence for an explicit analysis; no market/provider calls."""
    if not ticker.strip():
        raise HTTPException(status_code=400, detail="ticker must not be empty")
    try:
        return build_decision_history(
            PersonalHistoryService(settings.data_dir), result={}, tickers=(ticker,),
            as_of=as_of, since=since,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/options/ledger")
def option_brokerage_ledger() -> dict[str, Any]:
    """Expose canonical note cash flows with provenance; no inferred realized P&L."""
    ledger_path = settings.data_dir / "options.sqlite3"
    if not ledger_path.exists():
        return {"status": "NOT_AVAILABLE", "operations": []}
    operations = [
        {
            "transaction_id": item.transaction_id,
            "instrument_type": "OPTION",
            "option_ticker": item.option_ticker,
            "side": item.side,
            "quantity": item.absolute_quantity,
            "execution_price": item.execution_price,
            "cash_flow": -item.total_amount if item.total_amount is not None else None,
            "trade_date": item.as_of.isoformat() if item.as_of else None,
            "broker": item.broker,
            "note_number": item.note_number,
            "source_ref": item.source_ref,
        }
        for item in OptionTransactionLedger(ledger_path).list_all()
        if item.source_type == "BROKERAGE_NOTE" or item.source_ref.startswith("BTG:NotaCorretagem:")
    ]
    stock_transactions = _transaction_repository().list_by_source_prefix("BTG:NotaCorretagem:")
    operations.extend(
        {
            "transaction_id": item.transaction_id,
            "instrument_type": "STOCK",
            "option_ticker": item.ticker,
            "side": item.action,
            "quantity": item.quantity,
            "execution_price": item.price,
            "cash_flow": round(item.price * item.quantity * (-1 if item.action == "BUY" else 1), 2),
            "trade_date": item.executed_at.date().isoformat(),
            "broker": item.broker,
            "note_number": item.source_ref.split(":")[2] if len(item.source_ref.split(":")) > 2 else None,
            "source_ref": item.source_ref,
        }
        for item in stock_transactions
        if item.instrument_type == "STOCK"
    )
    operations.sort(key=lambda row: (row["trade_date"] or "", row["transaction_id"]))
    return {"status": "VALIDATED" if operations else "NOT_AVAILABLE", "operations": operations}


class CapitalProfileRequest(BaseModel):
    available_capital: float = Field(ge=0)
    minimum_reserve: float = Field(ge=0)


def _capital_connection() -> sqlite3.Connection:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    # Manual business state belongs in the existing canonical structured store.
    database = settings.data_dir / "b3_agent.db"
    SQLiteStore(database).initialize()
    return sqlite3.connect(database)


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
        connection.execute("INSERT INTO capital_profile (account, available, reserve, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(account) DO UPDATE SET available=excluded.available, reserve=excluded.reserve, updated_at=excluded.updated_at", ("BTG", request.available_capital, request.minimum_reserve, datetime.now(timezone.utc).isoformat()))
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

        parser = BrokerageNoteParser()
        transactions = parser.parse(temp_path)
        stock_transactions = parser.parse_stocks(temp_path)
        if not transactions and not stock_transactions:
            raise ValueError("nota sem operações de ações ou opções suportadas")
        source_fingerprint = hashlib.sha256(temp_path.read_bytes()).hexdigest()
        temp_path.replace(target)

        ledger_path = settings.data_dir / "options.sqlite3"
        inserted_options = OptionTransactionLedger(ledger_path).append(transactions)
        inserted_stocks = _transaction_repository().append_many(stock_transactions)

        first_source_ref = transactions[0].source_ref if transactions else stock_transactions[0].source_ref
        note_number = (
            transactions[0].note_number if transactions else first_source_ref.split(":")[2]
        )
        source_ref = first_source_ref.split(f":{safe_name}")[0]
        trade_dates = [item.as_of for item in transactions if item.as_of is not None]
        trade_dates.extend(item.executed_at.date() for item in stock_transactions)
        all_transactions = (*transactions, *stock_transactions)
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
                record_count=len(all_transactions),
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
            "parsed_count": len(all_transactions),
            "inserted_count": inserted_options + inserted_stocks,
            "transaction_ids": [item.transaction_id for item in all_transactions],
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
    """Append stock and option executions from a brokerage note to their ledgers."""
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
            "brapi_token_configured": bool(os.getenv("BRAPI_TOKEN")),
        },
    }


@app.get("/runtime/status")
def runtime_status() -> dict[str, Any]:
    """Expose the operational runtime state through the Orchestrator."""
    return RuntimeManager().status(health_override="ok")

class SchedulerConfigRequest(BaseModel):
    start_time: str = Field(pattern=r"^(?:[01]\\d|2[0-3]):[0-5]\\d$")
    end_time: str = Field(pattern=r"^(?:[01]\\d|2[0-3]):[0-5]\\d$")


def _scheduler_config_path() -> Path:
    return settings.data_dir / "structured" / "collection_schedule.json"


@app.get("/admin/scheduler-config")
def get_scheduler_config() -> dict[str, Any]:
    path = _scheduler_config_path()
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            start_time = str(payload.get("start_time", "08:00"))
            end_time = str(payload.get("end_time", "19:00"))
            source = "admin"
        else:
            start_time = f"{int(os.getenv('B3_INTEL_ACTIVE_START_HOUR', '8')):02d}:00"
            end_time = f"{int(os.getenv('B3_INTEL_ACTIVE_END_HOUR', '19')):02d}:00"
            source = "environment"
        return {"start_time": start_time, "end_time": end_time,
                "timezone": os.getenv("B3_AGENT_TIMEZONE", "America/Sao_Paulo"),
                "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri"], "source": source}
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail=f"scheduler configuration unavailable: {exc}") from exc


@app.post("/admin/scheduler-config")
def save_scheduler_config(request: SchedulerConfigRequest) -> dict[str, Any]:
    if request.start_time >= request.end_time:
        raise HTTPException(status_code=422, detail="start_time must be earlier than end_time")
    path = _scheduler_config_path()
    payload = {"schema_version": 1, "start_time": request.start_time,
               "end_time": request.end_time, "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        temporary.replace(path)
        return get_scheduler_config()
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"scheduler configuration unavailable: {exc}") from exc


class CollectionUniverseRequest(BaseModel):
    tickers: list[str] = Field(default_factory=list, max_length=500)


@app.get("/admin/collection-universe")
def get_collection_universe() -> dict[str, Any]:
    try:
        return CollectionUniverseStore(settings.data_dir).snapshot()
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"collection universe unavailable: {exc}") from exc


@app.post("/admin/collection-universe")
def save_collection_universe(request: CollectionUniverseRequest) -> dict[str, Any]:
    store = CollectionUniverseStore(settings.data_dir)
    try:
        store.save(request.tickers)
        return store.snapshot()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"collection universe unavailable: {exc}") from exc


@app.get("/market/current/{ticker}")
def current_market_quote(ticker: str) -> dict[str, Any]:
    """Return the current OPLAB stock quote, separate from history."""
    try:
        provider = OplabAdapter()
        quote = provider.get_current_quote(ticker)
        return {
            "ticker": quote.ticker,
            "as_of": quote.observation_timestamp.isoformat(),
            "source": quote.source,
            "quote": asdict(quote),
            "reuse_telemetry": getattr(provider, "last_reuse_telemetry", {}),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/options/current/{ticker}")
def current_option_quotes(
    ticker: str,
    option_type: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Return compact current OPLAB option quotes for explicit selection."""
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    normalized_type = option_type.upper().strip() if option_type else None
    if normalized_type not in {None, "PUT", "CALL"}:
        raise HTTPException(status_code=400, detail="option_type must be PUT or CALL")
    try:
        as_of = datetime.now(timezone.utc)
        provider = OplabOptionsAdapter()
        contracts, quotes = provider.get_snapshot(ticker, as_of)
        quote_by_id = {item.option_id: item for item in quotes}
        rows = []
        for contract in contracts:
            if normalized_type and contract.option_type != normalized_type:
                continue
            if contract.expiration_date <= as_of.date():
                continue
            quote = quote_by_id.get(contract.option_id)
            if quote is None:
                continue
            if not any(
                value is not None
                for value in (quote.bid, quote.ask, quote.last, quote.mid)
            ):
                continue
            rows.append({
                "contract": asdict(contract),
                "quote": asdict(quote),
            "reuse_telemetry": getattr(provider, "last_reuse_telemetry", {}),
            })
        rows.sort(
            key=lambda row: (
                row["contract"]["expiration_date"],
                row["contract"]["strike"],
                row["contract"]["option_id"],
            )
        )
        return {
            "ticker": ticker.upper().strip(),
            "as_of": as_of.isoformat(),
            "source": "oplab",
            "option_type": normalized_type,
            "count": min(len(rows), limit),
            "options": rows[:limit],
            "reuse_telemetry": getattr(provider, "last_reuse_telemetry", {}),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/analysis/live/{ticker}")
def live_analysis(ticker: str) -> dict[str, Any]:
    """Return normalized live market/options analytics for one B3 underlying."""
    try:
        snapshot = LiveProviderService(history_days=395).load(
            ticker, include_current_quote=True, include_options=False
        )
        # OPLAB history becomes available to this response when acquisition completes.
        # Use that response-time cutoff so ingestion-time availability is not
        # incorrectly treated as future data.
        cutoff = datetime.now(timezone.utc)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("live snapshot as_of must be timezone-aware")

        def available_by_cutoff(record: Any) -> bool:
            observed = record.observation_timestamp
            if observed.tzinfo is None or observed.utcoffset() is None:
                observed = observed.replace(tzinfo=timezone.utc)
            return observed <= cutoff and record.is_available_at(cutoff)

        eligible_history = sorted(
            (record for record in snapshot.market_records if available_by_cutoff(record)),
            key=lambda item: item.observation_timestamp,
        )
        if not eligible_history:
            raise ValueError(f"no point-in-time market history available for {snapshot.ticker}")
        history_latest = eligible_history[-1]
        current_quote = snapshot.current_stock_quote
        if current_quote is not None and not available_by_cutoff(current_quote):
            current_quote = None
        display_latest = current_quote or history_latest
        bounded_history = eligible_history[-520:]
        quant = compute_quant_features(eligible_history, as_of=cutoff)
        return {
            "ticker": snapshot.ticker,
            "as_of": cutoff.isoformat(),
            "source_refs": list(snapshot.source_refs),
            "market": {
                "history_count": len(eligible_history),
                "requested_history_days": 395,
                "price_history": [asdict(item) for item in bounded_history],
                "quant": asdict(quant),
                "current_quote": asdict(current_quote) if current_quote is not None else None,
                "current_quote_status": "AVAILABLE" if current_quote is not None else "UNAVAILABLE",
                "history_latest": asdict(history_latest),
                "latest": asdict(display_latest),
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


@app.get("/fundamentals/{ticker}")
def current_fundamentals(ticker: str) -> dict[str, Any]:
    """Return source-labeled current fundamentals under the V4.4 source policy with explicit PIT limits."""
    normalized = ticker.upper().strip()
    if re.fullmatch(r"[A-Z]{4}\d{1,2}", normalized) is None:
        raise HTTPException(status_code=400, detail="invalid B3 ticker")
    as_of = datetime.now(timezone.utc)
    try:
        adapter = StockFundamentalsProvider()
        records = adapter.get_financial_data(normalized)
        as_of = datetime.now(timezone.utc)
        eligible = []
        excluded_future_count = 0
        for record in records:
            observed = record.observation_timestamp
            if observed.tzinfo is None or observed.utcoffset() is None:
                observed = observed.replace(tzinfo=timezone.utc)
            if observed > as_of or not record.is_available_at(as_of):
                excluded_future_count += 1
                continue
            eligible.append(record)
        return {
            "ticker": normalized,
            "as_of": as_of.isoformat(),
            "status": "AVAILABLE" if eligible else "NO_DATA",
            "metrics": [asdict(record) for record in eligible],
            "source_refs": list(dict.fromkeys(
                f"{record.source}:{record.source_record_id or record.metric}"
                for record in eligible
            )),
            "excluded_future_count": excluded_future_count,
            "provider_diagnostics": getattr(adapter, "diagnostics", []),
            "limitations": [
                "Current provider snapshots only; ingestion availability does not establish historical availability.",
                "This endpoint supplies fundamentals only; institutional reports and Yahoo consensus require their own sourced research data.",
            ],
        }
    except (OSError, RuntimeError, ValueError) as exc:
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


@app.get("/intelligence/nightly/{ticker}")
def nightly_ticker_intelligence(ticker: str) -> dict[str, Any]:
    """Read the local DeepSeek research artifact with its evidence and timestamp."""
    normalized = ticker.strip().upper()
    if not normalized.isalnum() or not 5 <= len(normalized) <= 12:
        raise HTTPException(status_code=400, detail="invalid B3 ticker")
    path = settings.data_dir / "derived" / "nightly_intelligence" / f"{normalized}.json"
    if not path.is_file():
        return {"status": "NOT_AVAILABLE", "ticker": normalized}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"nightly artifact unavailable: {exc}") from exc
    if payload.get("ticker") != normalized or payload.get("status") != "completed":
        raise HTTPException(status_code=503, detail="nightly artifact has inconsistent identity or status")
    return payload


@app.get("/intelligence/pilot/{ticker}")
def pilot_ticker_intelligence(ticker: str) -> dict[str, Any]:
    """Read the evidence-backed DeepSeek/OpenClaw pilot for one stock."""
    normalized = ticker.strip().upper()
    if not normalized.isalnum() or not 5 <= len(normalized) <= 12:
        raise HTTPException(status_code=400, detail="invalid B3 ticker")
    path = settings.data_dir / "derived" / "intelligence_pilot_v41" / f"{normalized}.json"
    if not path.is_file():
        return {"ticker": normalized, "status": "NOT_AVAILABLE"}
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"pilot artifact unavailable: {exc}") from exc
    if result.get("ticker") != normalized:
        raise HTTPException(status_code=503, detail="pilot artifact identity mismatch")
    result["status"] = "COMPLETED" if result.get("deepseek_status") == result.get("openclaw_status") == "completed" else "PARTIAL"
    return result


@app.get("/intelligence/local/status")
def intelligence_local_status() -> dict[str, Any]:
    """Read continuous-intelligence cursor, queue and worker status."""
    return local_intelligence_status()


@app.get("/intelligence/local/queue")
def intelligence_local_queue() -> dict[str, Any]:
    """Read pending relevance and dossier queues without mutating them."""
    return local_intelligence_queues()


@app.get("/intelligence/local/manifest")
def intelligence_local_manifest() -> dict[str, Any]:
    """Read latest discovery, worker and reconciliation manifests."""
    return local_intelligence_manifests()


@app.get("/intelligence/local/{ticker}")
def intelligence_local_ticker(ticker: str) -> dict[str, Any]:
    """Read accepted local dossier and latest relevance screen for one ticker."""
    normalized = ticker.strip().upper()
    if re.fullmatch(r"[A-Z]{4}\d{1,2}", normalized) is None:
        raise HTTPException(status_code=400, detail="invalid B3 ticker")
    return local_ticker_intelligence(normalized)


@app.get("/version")
def version() -> dict[str, str]:
    return {"service": "b3-orchestrator-server", "version": app.version, "opportunity_screen_policy": "B3_OBSERVED_STOCK_SCREEN_V1"}


@app.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """Translate HTTP input to the transport-agnostic ``b3_orchestrator`` contract."""
    try:
        normalized = OrchestratorRequest.from_inputs(
            task=request.task,
            ticker=request.ticker,
            context=request.context,
        )
        from b3_agent.routing.lab_option_management import (
            compare_management, management_selection_from_turns,
        )
        management_context = management_selection_from_turns(normalized)
        if management_context is not None:
            if normalized.context.get('as_of') is not None:
                raise ValueError('Option management requires current portfolio and quotes')
            prior_selection, management_inputs = management_context
            import hashlib
            from datetime import datetime
            from zoneinfo import ZoneInfo
            from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
            from b3_agent.routing.lab_position import resolve_position
            from b3_agent.providers.oplab.options import OplabOptionsAdapter
            portfolio_path = settings.data_dir / 'imports' / 'portfolio.xlsx'
            revision = hashlib.sha256(portfolio_path.read_bytes()).hexdigest() if portfolio_path.is_file() else None
            portfolio = BtgRendaVariavelLoader().load(portfolio_path) if portfolio_path.is_file() else None
            as_of = datetime.now(timezone.utc)
            current = resolve_position({'option_id': prior_selection.get('option_id'),
                                        'quantity_units': prior_selection.get('selected_quantity_units')},
                                       portfolio, revision=revision,
                                       today=datetime.now(ZoneInfo('America/Sao_Paulo')).date())
            if current.get('lab_clarification'):
                return _response_to_model(OrchestratorResponse(status='NEEDS_CLARIFICATION', result=current))
            if revision is not None and hashlib.sha256(portfolio_path.read_bytes()).hexdigest() != revision:
                raise ValueError('Portfolio changed during option comparison; retry against the current snapshot')
            selected_id = current['lab_position_selection']['position']['position_id']
            position = next(p for p in portfolio.positions if p.position_id == selected_id)
            provider = OplabOptionsAdapter()
            underlying = position.underlying_ticker
            contracts, quotes = provider.get_snapshot(underlying, as_of)
            old_id = position.ticker.upper()
            old_contracts = [c for c in contracts if c.option_id.upper() == old_id]
            old_quotes = [q for q in quotes if q.option_id.upper() == old_id]
            if len(old_contracts) != 1 or len(old_quotes) != 1:
                raise ValueError('Current OPLAB chain has no unique identity and quote for the held option')
            destination_id = management_inputs.get('destination_option_id')
            if not destination_id:
                candidates = []
                for contract in contracts:
                    if contract.option_type.upper() != position.option_type.upper() or contract.expiration_date <= old_contracts[0].expiration_date:
                        continue
                    quote_matches = [q for q in quotes if q.option_id.upper() == contract.option_id.upper()]
                    if len(quote_matches) != 1:
                        continue
                    quote = quote_matches[0]
                    executable = quote.bid if position.quantity < 0 else quote.ask
                    if executable is None:
                        continue
                    try:
                        from b3_agent.routing.lab_option_management import _valid_contract_quote
                        _valid_contract_quote(contract, quote, option_id=contract.option_id.upper(),
                                              underlying=underlying.upper(), option_type=position.option_type.upper(),
                                              strike=None, expiration=contract.expiration_date, as_of=as_of)
                    except ValueError:
                        continue
                    candidates.append({'option_id': contract.option_id, 'option_type': contract.option_type,
                                       'strike': contract.strike, 'expiration_date': contract.expiration_date.isoformat(),
                                       'contract_multiplier': contract.contract_multiplier,
                                       'executable_side': 'BID' if position.quantity < 0 else 'ASK',
                                       'executable_quote_brl': executable,
                                       'quote_as_of': quote.observation_timestamp.isoformat(), 'source': quote.source})
                candidates.sort(key=lambda row: (row['expiration_date'], row['strike'], row['option_id']))
                clarification = {'lab_position_selection': current['lab_position_selection'],
                                 'lab_clarification': {'status': 'NEEDS_CLARIFICATION',
                                    'missing_fields': ['destination_option_id'],
                                    'question': 'Escolha o código exato do novo contrato de rolagem entre os contratos elegíveis abaixo.',
                                    'reason': 'A rolagem exige nova opção do mesmo ativo e tipo, com vencimento posterior. Nenhuma foi escolhida automaticamente.'},
                                 'lab_roll_candidates': candidates,
                                 'summary': 'Selecione o contrato de destino para calcular manter, encerrar e rolar.',
                                 'derived_synthesis_status': 'NOT_REQUESTED',
                                 'telemetry': {'llm_calls': 0, 'option_chain_calls': 1}}
                return _response_to_model(OrchestratorResponse(status='NEEDS_CLARIFICATION', result=clarification))
            destination_id = str(destination_id).upper().strip()
            destination_contracts = [c for c in contracts if c.option_id.upper() == destination_id]
            destination_quotes = [q for q in quotes if q.option_id.upper() == destination_id]
            if len(destination_contracts) != 1 or len(destination_quotes) != 1:
                raise ValueError('Selected destination contract is not uniquely available in the current OPLAB chain')
            result = compare_management(
                position=position, quantity_units=int(current['lab_position_selection']['selected_quantity_units']),
                old_contract=old_contracts[0], old_quote=old_quotes[0],
                new_contract=destination_contracts[0], new_quote=destination_quotes[0],
                portfolio=portfolio, portfolio_revision=revision or 'UNKNOWN', as_of=as_of,
                transaction_costs_brl=management_inputs.get('transaction_costs_brl'))
            result['telemetry'] = {'llm_calls': 0, 'option_chain_calls': 1}
            deterministic_only = normalized.context.get('analysis_mode') == 'deterministic'
            if deterministic_only:
                # OrchestratorResponse copies the result in __post_init__; set
                # the synthesis state before constructing that immutable response.
                result['derived_synthesis_status'] = 'NOT_REQUESTED'
            deterministic_response = OrchestratorResponse(status='COMPLETED', result=result,
                                                          sources=tuple(result['source_refs']))
            if deterministic_only:
                return _response_to_model(deterministic_response)
            synthesis_request = OrchestratorRequest(
                task=(f"Compare manter, encerrar ou rolar a posição de opção {old_id} "
                      f"para {destination_id}. Explique vantagens, contrapontos e condições "
                      "de mudança usando a comparação determinística fornecida; fluxo de caixa "
                      "não é lucro nem retorno esperado. Não recomende ordem."),
                ticker=underlying,
                context={**normalized.context, 'selected_ticker': underlying,
                         'response_guidance': (
                             'Explique a comparação determinística lab-option-management-v1. '
                             'Não altere preços, quantidades, lados, custos ou fontes. '
                             'Não trate fluxo incremental como lucro, retorno esperado ou recomendação. '
                             'Explicite dados UNKNOWN e limitações de comparação entre vencimentos.'
                         )},
            )
            return _response_to_model(_workspace_intelligence_response(
                synthesis_request, deterministic_response=deterministic_response))
        from b3_agent.routing.lab_position import position_intent, resolve_position
        position_inputs = position_intent(normalized)
        if position_inputs is not None:
            if normalized.context.get('as_of') is not None:
                raise ValueError('Position management requires the current portfolio; historical requests are not supported')
            import hashlib
            from datetime import datetime
            from zoneinfo import ZoneInfo
            from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
            portfolio_path = settings.data_dir / 'imports' / 'portfolio.xlsx'
            revision = hashlib.sha256(portfolio_path.read_bytes()).hexdigest() if portfolio_path.is_file() else None
            portfolio = BtgRendaVariavelLoader().load(portfolio_path) if portfolio_path.is_file() else None
            if revision is not None and hashlib.sha256(portfolio_path.read_bytes()).hexdigest() != revision:
                raise ValueError('Portfolio changed during selection; retry against the current snapshot')
            position_result = resolve_position(position_inputs, portfolio, revision=revision, today=datetime.now(ZoneInfo('America/Sao_Paulo')).date())
            status = 'NEEDS_CLARIFICATION' if position_result.get('lab_clarification') else 'INPUTS_IDENTIFIED'
            return _response_to_model(OrchestratorResponse(status=status, result=position_result))
        from b3_agent.routing.lab_clarification import lab_operation_clarification
        clarification = lab_operation_clarification(normalized)
        if clarification is not None:
            return _response_to_model(OrchestratorResponse(status='NEEDS_CLARIFICATION', result=clarification))
        normalized = explicit_stock_comparison(normalized)
        if normalized.context.get('funded_switch') is not None:
            if _workspace_name(normalized) != 'Strategy Lab' or normalized.context.get('as_of') is not None:
                raise ValueError('Funded switch supports current Strategy Lab requests only')
            from b3_agent.funded_switch import build_funded_switch
            inputs = normalized.context['funded_switch']
            assets = normalized.context.get('comparison_assets')
            if not isinstance(inputs, dict) or not isinstance(assets, list) or len(assets) != 2 or any(not isinstance(item,str) for item in assets):
                raise ValueError('Funded switch requires an explicit input object and two stock assets')
            from b3_agent.strategy_live import _validated_equity_ticker
            assets = [_validated_equity_ticker(item) for item in assets]
            result = build_funded_switch(assets, inputs)
            fast_response = OrchestratorResponse(status='COMPLETED', result=result, sources=tuple(result['source_refs']))
            normalized = OrchestratorRequest(task=normalized.task,ticker=None,context={**normalized.context,'selected_ticker':None})
            if normalized.context.get('analysis_mode') == 'deterministic':
                result['telemetry'] = {'llm_calls':0}
                result['derived_synthesis_status'] = 'NOT_REQUESTED'
                return _response_to_model(OrchestratorResponse(status='COMPLETED',result=result,sources=tuple(result['source_refs'])))
            return _response_to_model(_workspace_intelligence_response(normalized, deterministic_response=fast_response))
        fast_response = _dispatch_opportunity_screen(normalized)
        if fast_response is not None:
            if normalized.context.get('analysis_mode') == 'deterministic' or normalized.context.get('as_of') is not None:
                return _response_to_model(fast_response)
            from b3_agent.opportunity_materiality import build_opportunity_research_scope
            screen = fast_response.result['opportunity_screen']
            research_scope = build_opportunity_research_scope(
                screen, screen.get('requested_universe', ())
            )
            fast_response = OrchestratorResponse(
                status=fast_response.status,
                result={**fast_response.result, 'opportunity_research_scope':research_scope},
                sources=fast_response.sources, audit=fast_response.audit,
                error=fast_response.error,
            )
            normalized = OrchestratorRequest(task=normalized.task, ticker=None, context={
                **normalized.context, 'selected_ticker':None,
                'opportunity_assets':research_scope['context_tickers'],
                'opportunity_research_scope':research_scope,
            })
        else:
            fast_response = _dispatch_fast_route(normalized)
        if _uses_workspace_intelligence(normalized):
            response = _workspace_intelligence_response(
                normalized,
                deterministic_response=fast_response,
            )
            return _response_to_model(response)

        if fast_response is not None:
            return _response_to_model(fast_response)

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


@app.get("/providers/budget/brapi")
def brapi_budget_status() -> dict[str, Any]:
    """Local quota metadata only; never expose provider credentials."""
    return BrapiBudget().snapshot()
