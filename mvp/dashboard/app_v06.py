"""B3 Investment Copilot Dashboard V0.6 — lightweight UX prototype.

This is intentionally a shallow iteration for real-user feedback.
It reuses deterministic domain engines and loaders; it does not implement
new investment logic, Neo4j ingestion, or LLM orchestration.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from b3_agent.opportunity import OpportunityIntelligenceEngine
from b3_agent.options.brokerage_notes import BrokerageNoteParser
from b3_agent.options.lifecycle import OptionContract, build_option_lifecycles
from b3_agent.options.reconciliation import OptionsReconciliationEngine
from b3_agent.options.transactions import OptionsTransactionLoader
from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.option_contract_registry import OptionContractRecord, OptionContractRegistry
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.source_manifest import SourceManifestRecord, SourceManifestRepository
from b3_agent.repositories.portfolio import PortfolioRepository

st.set_page_config(page_title="B3 Investment Copilot", page_icon="📊", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_REGISTRY_PATH = Path(
    os.getenv(
        "B3_AGENT_OPTION_CONTRACT_REGISTRY_PATH",
        str(PROJECT_ROOT / "data" / "option_contracts.sqlite3"),
    )
).expanduser().resolve()

MANIFEST_PATH = Path(
    os.getenv(
        "B3_AGENT_SOURCE_MANIFEST_PATH",
        str(PROJECT_ROOT / "data" / "source_manifest.sqlite3"),
    )
).expanduser().resolve()

LEDGER_PATH = Path(
    os.getenv(
        "B3_AGENT_OPTION_LEDGER_PATH",
        str(PROJECT_ROOT / "data" / "option_transactions.sqlite3"),
    )
).expanduser().resolve()

# Streamlit has a native left sidebar; for this prototype we visually move it
# to the right so we can test the intended product layout before adopting a
# dedicated Windows shell.
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        left: auto !important;
        right: 0 !important;
        transform: none !important;
        border-left: 1px solid rgba(128,128,128,.25);
        border-right: none;
    }
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


def _load_brokerage_note(uploaded_file):
    path = _temp_path(uploaded_file)
    try:
        return BrokerageNoteParser().parse(path)
    finally:
        path.unlink(missing_ok=True)


def _load_transactions(uploaded_file):
    path = _temp_path(uploaded_file)
    try:
        return OptionsTransactionLoader().load(path)
    finally:
        path.unlink(missing_ok=True)


def _load_configured():
    configured = os.getenv("B3_AGENT_PORTFOLIO_FILE", "")
    if not configured:
        return None, "Nenhum Excel BTG configurado."
    path = Path(configured).expanduser().resolve()
    if not path.exists():
        return None, f"Arquivo não encontrado: {path}"
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return BtgRendaVariavelLoader().load(path), None
    return PortfolioRepository(path).load(), None


for key, default in {
    "context": None,
    "transactions": (),
    "btg_status": "Not loaded",
    "options_status": "Not loaded",
    "ledger_status": "Not loaded",
    "load_error": None,
    "ledger_initialized": False,
    "contract_registry": (),
    "source_manifest": (),
}.items():
    st.session_state.setdefault(key, default)


# The ledger is persistent storage, so it must be read on every new Streamlit
# session. Previously it was only read after clicking LOAD DATA, which made the
# history appear to disappear after a restart or a fresh browser session.
if not st.session_state.ledger_initialized:
    try:
        ledger = OptionTransactionLedger(LEDGER_PATH)
        st.session_state.transactions = ledger.list_all()
        registry = OptionContractRegistry(CONTRACT_REGISTRY_PATH)
        st.session_state.contract_registry = registry.list_all()
        manifest = SourceManifestRepository(MANIFEST_PATH)
        st.session_state.source_manifest = manifest.list_all()
        st.session_state.options_status = (
            f"✓ Ledger — {len(st.session_state.transactions)} transactions"
        )
        st.session_state.ledger_status = (
            f"✓ Persistent — {len(st.session_state.transactions)} transactions restored"
        )
    except Exception as exc:
        st.session_state.options_status = "✗ Ledger read failed"
        st.session_state.ledger_status = "✗ Persistent ledger unavailable"
        st.session_state.load_error = f"Ledger: {exc}"
    finally:
        st.session_state.ledger_initialized = True

with st.sidebar:
    st.header("DATA & COPILOT")
    st.caption("Prototype V0.6")

    st.markdown("#### Load Excel")
    btg_file = st.file_uploader("BTG Portfolio", type=["xlsx", "xlsm"], key="v06_btg")
    options_file = st.file_uploader(
        "Options Transactions",
        type=["xlsx", "xlsm"],
        key="v06_options",
    )
    note_files = st.file_uploader(
        "Brokerage Notes (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        key="v06_notes",
    )

    if st.button("📥 LOAD DATA", type="primary", use_container_width=True):
        st.session_state.load_error = None
        loaded = False
        if btg_file:
            try:
                st.session_state.context = _load_btg(btg_file)
                st.session_state.btg_status = (
                    f"✓ Loaded — {len(st.session_state.context.positions)} positions"
                )
                loaded = True
            except Exception as exc:
                st.session_state.btg_status = "✗ Load failed"
                st.session_state.load_error = f"BTG: {exc}"
        try:
            ledger = OptionTransactionLedger(LEDGER_PATH)
            inserted = 0
            if options_file:
                inserted += ledger.append(_load_transactions(options_file))
                loaded = True
            for note_file in note_files or []:
                inserted += ledger.append(_load_brokerage_note(note_file))
                loaded = True
            if st.session_state.context is not None:
                registry = OptionContractRegistry(CONTRACT_REGISTRY_PATH)
                records = []
                for position in st.session_state.context.positions:
                    if position.instrument_type != "OPTION":
                        continue
                    expiration = position.expiration_date
                    records.append(
                        OptionContractRecord(
                            option_ticker=position.ticker,
                            expiration_date=(pd.Timestamp(expiration).date() if pd.notna(expiration) else None),
                            option_type=position.option_type,
                            strike=position.strike,
                            underlying_ticker=position.underlying_ticker,
                            contract_multiplier=getattr(position, "contract_multiplier", None),
                            source_ref="BTG current portfolio",
                        )
                    )
                registry.upsert_many(records)
                st.session_state.contract_registry = registry.list_all()
            st.session_state.transactions = ledger.list_all()
            st.session_state.options_status = (
                f"✓ Ledger — {len(st.session_state.transactions)} transactions"
            )
            st.session_state.ledger_status = f"✓ Persisted — {inserted} new transactions"
        except Exception as exc:
            st.session_state.options_status = "✗ Ledger load failed"
            st.session_state.load_error = (
                (st.session_state.load_error or "") + f" | Ledger: {exc}"
            )
        if not loaded and not st.session_state.transactions and not st.session_state.context:
            st.session_state.load_error = "Selecione pelo menos um arquivo Excel."

    st.divider()
    st.markdown("#### Data status")
    st.write(f"**BTG:** {st.session_state.btg_status}")
    st.write(f"**Options:** {st.session_state.options_status}")
    st.write(f"**Ledger:** {st.session_state.ledger_status}")
    if st.session_state.load_error:
        st.error(st.session_state.load_error)

    st.divider()
    st.markdown("#### Knowledge")
    st.write("🟡 Obsidian")
    st.write("🟡 RAG")
    st.write("⚪ Neo4j — future integration")

    st.divider()
    st.markdown("#### Copilot")
    question = st.text_area(
        "Pergunta",
        placeholder="Ex.: quais opções tenho no portfolio?",
        height=80,
        key="v06_question",
    )
    if st.button("💬 Ask", use_container_width=True):
        if question.strip():
            st.info("Chat UI pronta. Orchestrator será conectado em uma iteração posterior.")
        else:
            st.warning("Digite uma pergunta.")

context = st.session_state.context
if context is None:
    context, error = _load_configured()
    if error:
        st.warning(error)
        st.info("Carregue o Excel BTG no painel DATA & COPILOT à direita para iniciar.")
        st.stop()

intelligence = PortfolioIntelligenceEngine().build(context)
rows = [
    {
        "Ticker": p.ticker,
        "Tipo": p.instrument_type,
        "Quantidade": p.quantity,
        "Preço atual": p.market_price,
        "Valor de mercado atual": p.market_value,
        "Vencimento": p.expiration_date,
        "Tipo opção": p.option_type,
        "Strike": p.strike,
        "Underlying": p.underlying_ticker,
    }
    for p in context.positions
]
df = pd.DataFrame(rows)
stock_df = df[df["Tipo"] == "STOCK"]
option_df = df[df["Tipo"] == "OPTION"].copy()
option_df["Tipo opção"] = option_df["Tipo opção"].fillna("").astype(str).str.upper()

market_value = float(df["Valor de mercado atual"].fillna(0).sum())
stock_value = float(stock_df["Valor de mercado atual"].fillna(0).sum())
option_value = float(option_df["Valor de mercado atual"].fillna(0).sum())

st.title("B3 Investment Copilot")
st.caption("V0.6 prototype • deterministic facts • read-only")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Market value", f"R$ {market_value:,.2f}")
c2.metric("Positions", len(df))
c3.metric("Stocks", len(stock_df))
c4.metric("Options", len(option_df))

st.divider()
tab_portfolio, tab_options, tab_opportunities, tab_intelligence = st.tabs(
    ["Portfolio", "Options Intelligence", "Opportunities", "Portfolio Intelligence"]
)

with tab_portfolio:
    st.subheader("Portfolio")
    st.caption(f"As of {context.as_of} • {context.quality_status}")
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab_options:
    st.subheader("Options Intelligence")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current options", len(option_df))
    c2.metric("Puts", int((option_df["Tipo opção"] == "PUT").sum()))
    c3.metric("Calls", int((option_df["Tipo opção"] == "CALL").sum()))
    c4.metric("Assignment capital", f"R$ {intelligence.capital_risk.assignment_capital:,.2f}")

    st.markdown("#### Current option positions")
    st.dataframe(option_df, use_container_width=True, hide_index=True)

    transactions = tuple(st.session_state.transactions or ())
    if transactions:
        reconciliation = OptionsReconciliationEngine().reconcile(transactions, context)

        st.markdown("#### Transaction history")
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("Transactions loaded", len(transactions))
        tc2.metric("Linked to current positions", len(reconciliation.current))
        tc3.metric("Historical only", len(reconciliation.historical_only))
        tc4.metric("Potential duplicates", len(reconciliation.potential_cross_source_duplicates))

        if reconciliation.potential_cross_source_duplicates:
            st.markdown("#### Cross-source duplicate candidates")
            duplicate_rows = [
                {
                    "Excel transaction": excel_id,
                    "BTG note transaction": note_id,
                    "Status": "REVIEW — not merged",
                }
                for excel_id, note_id in reconciliation.potential_cross_source_duplicates
            ]
            st.dataframe(
                pd.DataFrame(duplicate_rows),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Candidatos são identificados por ticker, quantidade, preço e valor total. "
                "O sistema não remove nem mescla registros automaticamente."
            )

        transaction_rows = [
            {
                "Trade date": tx.as_of,
                "Note": tx.note_number or "",
                "Transaction ID": tx.transaction_id,
                "Ticker": tx.option_ticker,
                "Side": tx.side,
                "Quantity": tx.absolute_quantity,
                "Execution price": tx.execution_price,
                "Total amount": tx.total_amount,
                "Broker": tx.broker,
                "Source": tx.source_ref,
            }
            for tx in transactions
        ]
        st.dataframe(
            pd.DataFrame(transaction_rows),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Histórico preserva Custo Médio como preço de execução e Custo Total como valor "
            "da transação. Uma transação individual não é tratada como a posição atual."
        )

        st.markdown("#### History coverage")
        coverage_rows = [
            {
                "Ticker": item.option_ticker,
                "First trade": item.first_trade_date,
                "Last trade": item.last_trade_date,
                "Transactions": item.transaction_count,
                "Net history qty": item.net_historical_quantity,
                "Current qty": item.current_position_quantity,
                "Position alignment": item.position_alignment,
                "Completeness": item.completeness,
            }
            for item in reconciliation.history_coverage
        ]
        st.dataframe(
            pd.DataFrame(coverage_rows),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "ALIGNED significa que a quantidade líquida do histórico coincide com a posição BTG. "
            "Isso não prova que o histórico contém a operação de abertura; por isso Completeness "
            "permanece UNKNOWN até existir evidência explícita de cobertura da fonte."
        )

        st.markdown("#### Option lifecycle")
        registry = OptionContractRegistry(CONTRACT_REGISTRY_PATH)
        contract_records = registry.list_all()
        contracts = {
            record.option_ticker: OptionContract(
                option_ticker=record.option_ticker,
                expiration_date=record.expiration_date,
                option_type=record.option_type,
                strike=record.strike,
                underlying_ticker=record.underlying_ticker,
                contract_multiplier=record.contract_multiplier,
            )
            for record in contract_records
            if record.expiration_date is not None
        }

        lifecycle_rows = []
        for lifecycle in build_option_lifecycles(
            transactions,
            contracts=contracts,
            evaluation_date=max(
                (tx.as_of for tx in transactions if tx.as_of is not None),
                default=context.as_of,
            ),
        ):
            lifecycle_rows.append(
                {
                    "Ticker": lifecycle.option_ticker,
                    "Status": lifecycle.status,
                    "Net qty (history)": lifecycle.net_quantity,
                    "Closed qty": lifecycle.closed_quantity,
                    "Open/unmatched qty": lifecycle.unmatched_quantity,
                    "Realized P&L": lifecycle.realized_pnl,
                    "Expiration": lifecycle.expiration_date,
                    "Expiry state": lifecycle.expiry_state,
                    "History": lifecycle.history_completeness,
                    "Contract metadata": lifecycle.contract_metadata_quality,
                    "P&L basis": lifecycle.pnl_basis,
                }
            )
        st.dataframe(
            pd.DataFrame(lifecycle_rows),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Lifecycle é reconstruído apenas a partir das transações importadas. "
            "Quando o vencimento passou mas não temos o evento de exercício/atribuição, "
            "o status permanece EXPIRED_UNRESOLVED; o sistema não assume que a opção "
            "expirou sem valor."
        )
    else:
        st.info("Nenhum histórico de transações de opções carregado.")

    st.caption("Valores da posição atual vêm do PortfolioContext; nenhum multiplicador ou contrato é inferido pelo dashboard.")

with tab_opportunities:
    st.subheader("Opportunities")
    opportunity_set = OpportunityIntelligenceEngine().assess(())
    c1, c2 = st.columns(2)
    c1.metric("Eligible", len(opportunity_set.ranked_opportunities))
    c2.metric("Rejected", len(opportunity_set.rejected_opportunities))
    st.info(
        "Opportunity producers ainda não estão conectados a esta UI. "
        "Nenhuma oportunidade é inventada a partir da exposição do portfolio."
    )

with tab_intelligence:
    st.subheader("Portfolio Intelligence")
    st.write("Deterministic intelligence shared with the domain/MCP layer.")
    st.metric("Valor em ações", f"R$ {stock_value:,.2f}")
    st.metric("Valor em opções", f"R$ {option_value:,.2f}")
    exposures = [
        {
            "Ticker": e.ticker,
            "Valor líquido": e.net_market_value,
            "Peso": e.weight,
            "Opções": e.option_count,
            "Short options": e.short_option_count,
            "Assignment capital": e.assignment_capital,
        }
        for e in getattr(intelligence, "exposures", ())
    ]
    if exposures:
        st.dataframe(pd.DataFrame(exposures), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma exposição calculada.")

st.divider()
st.caption(
    f"As of: {context.as_of} • Quality: {context.quality_status} • "
    f"Sources: {', '.join(context.source_refs)}"
)
st.caption("Prototype only • no order execution • no LLM override of deterministic facts")
