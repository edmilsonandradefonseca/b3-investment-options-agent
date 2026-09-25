"""B3 Investment Copilot Dashboard V0.7 — real-data analytical dashboard.

The UI exposes deterministic information extracted from the loaded portfolio,
option transaction ledger, contract registry and source manifest. It does not
invent market data or recommendations.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from b3_agent.options.brokerage_notes import BrokerageNoteParser
from b3_agent.options.lifecycle import OptionContract, build_option_lifecycles
from b3_agent.options.reconciliation import (
    OptionsReconciliationEngine,
    TransactionSourceCoverage,
)
from b3_agent.options.transactions import OptionsTransactionLoader
from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.option_contract_registry import (
    OptionContractRecord,
    OptionContractRegistry,
)
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.portfolio import PortfolioRepository
from b3_agent.repositories.source_manifest import (
    SourceManifestRecord,
    SourceManifestRepository,
)

st.set_page_config(
    page_title="B3 Investment Copilot",
    page_icon="📊",
    layout="wide",
)

ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = Path(
    os.getenv(
        "B3_AGENT_OPTION_LEDGER_PATH",
        str(ROOT / "data" / "option_transactions.sqlite3"),
    )
).expanduser().resolve()
REGISTRY_PATH = Path(
    os.getenv(
        "B3_AGENT_OPTION_CONTRACT_REGISTRY_PATH",
        str(ROOT / "data" / "option_contracts.sqlite3"),
    )
).expanduser().resolve()
MANIFEST_PATH = Path(
    os.getenv(
        "B3_AGENT_SOURCE_MANIFEST_PATH",
        str(ROOT / "data" / "source_manifest.sqlite3"),
    )
).expanduser().resolve()

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: rgba(30, 100, 180, .08);
        border: 1px solid rgba(100, 150, 200, .20);
        padding: .75rem;
        border-radius: 12px;
    }
    .section-title {font-size: 1.15rem; font-weight: 700; margin-top: .6rem;}
    .muted {color: #718096; font-size: .86rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _temp_path(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix or ".xlsx"
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(uploaded_file.getvalue())
    handle.close()
    return Path(handle.name)


def _load_btg(uploaded_file):
    path = _temp_path(uploaded_file)
    try:
        return BtgRendaVariavelLoader().load(path)
    finally:
        path.unlink(missing_ok=True)


def _load_options(uploaded_file):
    path = _temp_path(uploaded_file)
    try:
        return OptionsTransactionLoader().load(path)
    finally:
        path.unlink(missing_ok=True)


def _load_note(uploaded_file):
    path = _temp_path(uploaded_file)
    try:
        return BrokerageNoteParser().parse(path)
    finally:
        path.unlink(missing_ok=True)


def _load_configured():
    configured = os.getenv("B3_AGENT_PORTFOLIO_FILE", "")
    if not configured:
        return None, "Nenhum Excel BTG configurado."
    path = Path(configured).expanduser().resolve()
    if not path.exists():
        return None, f"Arquivo não encontrado: {path}"
    return BtgRendaVariavelLoader().load(path), None


for key, default in {
    "context": None,
    "transactions": (),
    "contract_registry": (),
    "source_manifest": (),
    "error": None,
    "loaded": False,
}.items():
    st.session_state.setdefault(key, default)

ledger = OptionTransactionLedger(LEDGER_PATH)
registry = OptionContractRegistry(REGISTRY_PATH)
manifest = SourceManifestRepository(MANIFEST_PATH)

if not st.session_state.loaded:
    st.session_state.transactions = ledger.list_all()
    st.session_state.contract_registry = registry.list_all()
    st.session_state.source_manifest = manifest.list_all()
    st.session_state.loaded = True

with st.sidebar:
    st.header("📊 B3 Investment Copilot")
    st.caption("V0.7 • real data • deterministic analysis")

    btg_file = st.file_uploader(
        "BTG Portfolio",
        type=["xlsx", "xlsm"],
        key="v07_btg",
    )
    options_file = st.file_uploader(
        "Options Transactions",
        type=["xlsx", "xlsm"],
        key="v07_options",
    )
    note_files = st.file_uploader(
        "Brokerage Notes",
        type=["pdf"],
        accept_multiple_files=True,
        key="v07_notes",
    )

    if st.button("📥 LOAD DATA", type="primary", use_container_width=True):
        st.session_state.error = None
        try:
            if btg_file:
                st.session_state.context = _load_btg(btg_file)

            inserted = 0
            if options_file:
                txs = _load_options(options_file)
                inserted += ledger.append(txs)
                manifest.upsert(
                    SourceManifestRecord(
                        source_fingerprint=hashlib.sha256(
                            options_file.getvalue()
                        ).hexdigest(),
                        source_type="OPTIONS_XLSX",
                        source_id=options_file.name,
                        source_ref="Options Transactions XLSX",
                        file_name=options_file.name,
                        imported_at=datetime.now(),
                        record_count=len(txs),
                    )
                )

            for note_file in note_files or []:
                txs = _load_note(note_file)
                inserted += ledger.append(txs)
                dates = [tx.as_of for tx in txs if tx.as_of is not None]
                note_number = txs[0].note_number if txs else note_file.name
                manifest.upsert(
                    SourceManifestRecord(
                        source_fingerprint=hashlib.sha256(
                            note_file.getvalue()
                        ).hexdigest(),
                        source_type="BROKERAGE_NOTE",
                        source_id=note_number or note_file.name,
                        source_ref=(
                            f"BTG:NotaCorretagem:{note_number}"
                            if note_number
                            else note_file.name
                        ),
                        file_name=note_file.name,
                        imported_at=datetime.now(),
                        record_count=len(txs),
                        coverage_start=min(dates) if dates else None,
                        coverage_end=max(dates) if dates else None,
                    )
                )

            if st.session_state.context is not None:
                records = []
                for p in st.session_state.context.positions:
                    if p.instrument_type != "OPTION":
                        continue
                    records.append(
                        OptionContractRecord(
                            option_ticker=p.ticker,
                            expiration_date=p.expiration_date,
                            option_type=p.option_type,
                            strike=p.strike,
                            underlying_ticker=p.underlying_ticker,
                            contract_multiplier=p.contract_multiplier,
                            source_ref="BTG current portfolio",
                        )
                    )
                registry.upsert_many(records)

            st.session_state.transactions = ledger.list_all()
            st.session_state.contract_registry = registry.list_all()
            st.session_state.source_manifest = manifest.list_all()
            st.success(f"Dados carregados. {inserted} novas transações.")
        except Exception as exc:
            st.session_state.error = str(exc)

    st.divider()
    st.markdown("**Dados persistidos**")
    st.write(f"Transações: **{len(st.session_state.transactions)}**")
    st.write(f"Contratos: **{len(st.session_state.contract_registry)}**")
    st.write(f"Fontes: **{len(st.session_state.source_manifest)}**")

    st.divider()
    st.caption(
        "O Dashboard mostra fatos extraídos e análises determinísticas. "
        "Não executa ordens."
    )

context = st.session_state.context
if context is None:
    context, error = _load_configured()
    if error:
        st.info("Carregue o Excel BTG para começar.")
        if st.session_state.error:
            st.error(st.session_state.error)
        st.stop()

intelligence = PortfolioIntelligenceEngine().build(context)
transactions = tuple(st.session_state.transactions or ())
manifest_records = tuple(st.session_state.source_manifest or ())

source_coverage = tuple(
    TransactionSourceCoverage(
        source_ref=r.source_ref,
        coverage_start=r.coverage_start,
        coverage_end=r.coverage_end,
        scope=r.scope,
        completeness=r.completeness,
    )
    for r in manifest_records
)

reconciliation = OptionsReconciliationEngine().reconcile(
    transactions,
    context,
    source_coverage=source_coverage,
)

positions = pd.DataFrame(
    [
        {
            "Ticker": p.ticker,
            "Type": p.instrument_type,
            "Qty": p.quantity,
            "Avg cost": p.average_cost,
            "Market price": p.market_price,
            "Market value": p.market_value,
            "P&L": (
                (p.market_price - p.average_cost) * p.quantity
                if p.average_cost is not None and p.market_price is not None
                and p.instrument_type != "OPTION"
                else None
            ),
            "Option type": p.option_type,
            "Strike": p.strike,
            "Expiration": p.expiration_date,
            "Underlying": p.underlying_ticker,
        }
        for p in context.positions
    ]
)

stocks = positions[positions["Type"] != "OPTION"]
options = positions[positions["Type"] == "OPTION"]
market_value = float(positions["Market value"].fillna(0).sum())
stock_value = float(stocks["Market value"].fillna(0).sum())
option_value = float(options["Market value"].fillna(0).sum())
short_option_value = float(
    options.loc[options["Qty"] < 0, "Market value"].fillna(0).sum()
)
total_pnl = float(positions["P&L"].fillna(0).sum())
short_puts = options[
    (options["Qty"] < 0) & (options["Option type"].fillna("").str.upper() == "PUT")
]
assignment_capital = float(
    sum(
        abs(p.quantity) * (p.strike or 0) * p.contract_multiplier
        for p in context.positions
        if p.instrument_type == "OPTION"
        and p.quantity < 0
        and (p.option_type or "").upper() == "PUT"
    )
)

st.title("B3 Investment Copilot")
st.caption(
    f"Snapshot {context.as_of} • {context.quality_status} • "
    f"{len(positions)} positions"
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Market value", f"R$ {market_value:,.2f}")
c2.metric("Cash", f"R$ {context.cash:,.2f}")
c3.metric("Stocks", f"R$ {stock_value:,.2f}")
c4.metric("Options", f"R$ {option_value:,.2f}")
c5.metric("Position P&L", f"R$ {total_pnl:,.2f}")

tabs = st.tabs(
    [
        "Portfolio",
        "Options Intelligence",
        "What was extracted",
        "Analysis",
    ]
)

with tabs[0]:
    st.subheader("Portfolio overview")

    left, right = st.columns([1.4, 1])
    with left:
        st.markdown("#### Largest positions")
        top = positions.sort_values("Market value", ascending=False).head(10)
        st.dataframe(
            top[
                ["Ticker", "Type", "Qty", "Avg cost", "Market price", "Market value", "P&L"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with right:
        st.markdown("#### Allocation")
        allocation = pd.DataFrame(
            {
                "Category": ["Stocks", "Long options", "Short options", "Cash"],
                "Value": [
                    stock_value,
                    float(options.loc[options["Qty"] > 0, "Market value"].fillna(0).sum()),
                    abs(short_option_value),
                    context.cash,
                ],
            }
        )
        st.bar_chart(allocation.set_index("Category"))

    st.markdown("#### Underlying exposures")
    exposure_rows = [
        {
            "Underlying": e.ticker,
            "Net market value": e.net_market_value,
            "Weight": e.weight,
            "Options": e.option_count,
            "Short options": e.short_option_count,
            "Assignment capital": e.assignment_capital,
            "Covered calls": e.covered_call_contracts,
            "Call coverage": e.call_coverage_ratio,
        }
        for e in intelligence.exposures
    ]
    st.dataframe(
        pd.DataFrame(exposure_rows),
        use_container_width=True,
        hide_index=True,
    )

with tabs[1]:
    st.subheader("Options Intelligence")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current options", len(options))
    c2.metric("Short puts", len(short_puts))
    c3.metric("Assignment capital", f"R$ {assignment_capital:,.2f}")
    c4.metric("Transaction history", len(transactions))

    st.markdown("#### Current option positions")
    st.dataframe(
        options[
            [
                "Ticker",
                "Qty",
                "Market price",
                "Market value",
                "Option type",
                "Strike",
                "Expiration",
                "Underlying",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    if transactions:
        st.markdown("#### History reconciliation")
        r1, r2, r3 = st.columns(3)
        r1.metric("Linked history", len(reconciliation.current))
        r2.metric("Historical only", len(reconciliation.historical_only))
        r3.metric("Duplicate candidates", len(reconciliation.potential_cross_source_duplicates))

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Ticker": x.option_ticker,
                        "First trade": x.first_trade_date,
                        "Last trade": x.last_trade_date,
                        "Transactions": x.transaction_count,
                        "Net history qty": x.net_historical_quantity,
                        "Current qty": x.current_position_quantity,
                        "Alignment": x.position_alignment,
                        "Completeness": x.completeness,
                    }
                    for x in reconciliation.history_coverage
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Option lifecycle")
        contract_records = registry.list_all()
        contracts = {
            r.option_ticker: OptionContract(
                option_ticker=r.option_ticker,
                expiration_date=r.expiration_date,
                option_type=r.option_type,
                strike=r.strike,
                underlying_ticker=r.underlying_ticker,
                contract_multiplier=r.contract_multiplier,
            )
            for r in contract_records
            if r.expiration_date is not None
        }
        lifecycles = build_option_lifecycles(
            transactions,
            contracts=contracts,
            evaluation_date=context.as_of,
        )
        lifecycle_df = pd.DataFrame(
            [
                {
                    "Ticker": x.option_ticker,
                    "Status": x.status,
                    "Net qty": x.net_quantity,
                    "Closed qty": x.closed_quantity,
                    "Unmatched qty": x.unmatched_quantity,
                    "Realized P&L": x.realized_pnl,
                    "Expiration": x.expiration_date,
                    "History": x.history_completeness,
                    "Contract metadata": x.contract_metadata_quality,
                }
                for x in lifecycles
            ]
        )
        st.dataframe(lifecycle_df, use_container_width=True, hide_index=True)

        st.markdown("#### Source manifest")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Type": r.source_type,
                        "ID": r.source_id,
                        "File": r.file_name,
                        "Records": r.record_count,
                        "Coverage start": r.coverage_start,
                        "Coverage end": r.coverage_end,
                        "Scope": r.scope,
                        "Completeness": r.completeness,
                    }
                    for r in manifest_records
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

with tabs[2]:
    st.subheader("What the system extracted")

    st.markdown("#### Portfolio facts")
    st.write(
        f"**{len(positions)} positions** from the authoritative portfolio snapshot "
        f"dated **{context.as_of}**."
    )
    st.write(
        f"Stocks: **{len(stocks)}** • Options: **{len(options)}** • "
        f"Cash: **R$ {context.cash:,.2f}**"
    )

    st.markdown("#### Transaction facts")
    if transactions:
        tx_df = pd.DataFrame(
            [
                {
                    "Date": tx.as_of,
                    "Ticker": tx.option_ticker,
                    "Side": tx.side,
                    "Qty": tx.absolute_quantity,
                    "Execution price": tx.execution_price,
                    "Total amount": tx.total_amount,
                    "Source": tx.source_type,
                    "Source ID": tx.source_id,
                }
                for tx in transactions
            ]
        )
        st.dataframe(tx_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma transação persistida.")

    st.markdown("#### Data quality")
    quality = pd.DataFrame(
        [
            {"Check": "Portfolio snapshot", "Result": context.quality_status},
            {"Check": "Transaction ledger", "Result": f"{len(transactions)} records"},
            {"Check": "Source manifest", "Result": f"{len(manifest_records)} sources"},
            {
                "Check": "History completeness",
                "Result": (
                    "Explicit evidence required; alignment alone is not completeness."
                ),
            },
        ]
    )
    st.dataframe(quality, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Deterministic analysis")

    insights = []

    if len(positions):
        largest = positions.sort_values("Market value", ascending=False).iloc[0]
        insights.append(
            f"Maior posição por valor de mercado: {largest['Ticker']} "
            f"(R$ {largest['Market value']:,.2f})."
        )

    if assignment_capital:
        insights.append(
            f"Capital de atribuição associado às puts vendidas identificadas: "
            f"R$ {assignment_capital:,.2f}."
        )

    if len(reconciliation.historical_only):
        insights.append(
            f"Existem {len(reconciliation.historical_only)} transações históricas "
            "cujos tickers não aparecem na posição BTG atual."
        )

    complete = sum(
        x.completeness == "COMPLETE" for x in reconciliation.history_coverage
    )
    unknown = sum(
        x.completeness == "UNKNOWN" for x in reconciliation.history_coverage
    )
    insights.append(
        f"Na cobertura de histórico, {complete} tickers têm evidência explícita de "
        f"completude e {unknown} permanecem como UNKNOWN."
    )

    open_count = 0
    closed_count = 0
    expired_unresolved = 0
    if transactions:
        contract_records = registry.list_all()
        contracts = {
            r.option_ticker: OptionContract(
                option_ticker=r.option_ticker,
                expiration_date=r.expiration_date,
                option_type=r.option_type,
                strike=r.strike,
                underlying_ticker=r.underlying_ticker,
                contract_multiplier=r.contract_multiplier,
            )
            for r in contract_records
            if r.expiration_date is not None
        }
        for x in build_option_lifecycles(
            transactions, contracts=contracts, evaluation_date=context.as_of
        ):
            open_count += x.status == "OPEN"
            closed_count += x.status == "CLOSED"
            expired_unresolved += x.status == "EXPIRED_UNRESOLVED"

    insights.append(
        f"Lifecycle reconstruído: {open_count} OPEN, {closed_count} CLOSED e "
        f"{expired_unresolved} EXPIRED_UNRESOLVED."
    )

    for item in insights:
        st.info(item)

    st.markdown("#### Analysis boundaries")
    st.caption(
        "Estas análises são derivadas apenas dos dados carregados. "
        "O dashboard não usa cotação externa, volatilidade implícita, notícias "
        "ou previsão de mercado nesta versão."
    )

st.divider()
st.caption(
    f"Source: {', '.join(context.source_refs)} • "
    "No order execution • deterministic facts first"
)
