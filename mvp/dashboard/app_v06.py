"""B3 Investment Copilot Dashboard V0.6 — lightweight UX prototype.

This is intentionally a shallow iteration for real-user feedback.
It reuses deterministic domain engines and loaders; it does not implement
new investment logic, Neo4j ingestion, or LLM orchestration.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from b3_agent.opportunity import OpportunityIntelligenceEngine
from b3_agent.options.reconciliation import OptionsReconciliationEngine
from b3_agent.options.transactions import OptionsTransactionLoader
from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.portfolio import PortfolioRepository

st.set_page_config(page_title="B3 Investment Copilot", page_icon="📊", layout="wide")

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
    "load_error": None,
}.items():
    st.session_state.setdefault(key, default)

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
        if options_file:
            try:
                st.session_state.transactions = _load_transactions(options_file)
                st.session_state.options_status = (
                    f"✓ Loaded — {len(st.session_state.transactions)} transactions"
                )
                loaded = True
            except Exception as exc:
                st.session_state.options_status = "✗ Load failed"
                suffix = f" | Options: {exc}"
                st.session_state.load_error = (st.session_state.load_error or "") + suffix
        if not loaded:
            st.session_state.load_error = "Selecione pelo menos um arquivo Excel."

    st.divider()
    st.markdown("#### Data status")
    st.write(f"**BTG:** {st.session_state.btg_status}")
    st.write(f"**Options:** {st.session_state.options_status}")
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
option_value = float(option_df["Valor de mercado"].fillna(0).sum())

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
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Transactions loaded", len(transactions))
        tc2.metric("Linked to current positions", len(reconciliation.current))
        tc3.metric("Historical only", len(reconciliation.historical_only))

        transaction_rows = [
            {
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
