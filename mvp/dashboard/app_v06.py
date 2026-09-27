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

from b3_agent.dashboard_e2e import DashboardE2EService
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
    "intelligence": None,
    "opportunities": None,
    "btg_status": "Not loaded",
    "options_status": "Not loaded",
    "load_error": None,
}.items():
    st.session_state.setdefault(key, default)

with st.sidebar:
    st.header("DATA & COPILOT")
    st.caption("V4 E2E • read-only")

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
            portfolio_path = _temp_path(btg_file)
            options_path = _temp_path(options_file) if options_file else None
            try:
                snapshot = DashboardE2EService().load(
                    portfolio_path,
                    options_path=options_path,
                )
                st.session_state.context = snapshot.portfolio
                st.session_state.intelligence = snapshot.portfolio_intelligence
                st.session_state.transactions = snapshot.option_transactions
                st.session_state.opportunities = snapshot.opportunities
                st.session_state.btg_status = (
                    f"✓ Loaded — {len(snapshot.portfolio.positions)} positions"
                )
                st.session_state.options_status = (
                    f"✓ Loaded — {len(snapshot.option_transactions)} transactions"
                    if options_file else "Not loaded"
                )
                loaded = True
            except Exception as exc:
                st.session_state.btg_status = "✗ Load failed"
                if options_file:
                    st.session_state.options_status = "✗ Load failed"
                st.session_state.load_error = f"E2E load: {exc}"
            finally:
                portfolio_path.unlink(missing_ok=True)
                if options_path is not None:
                    options_path.unlink(missing_ok=True)
        elif options_file:
            st.session_state.load_error = (
                "Carregue o BTG Portfolio junto com Options Transactions "
                "para montar um snapshot E2E consistente."
            )
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
    st.write("🟢 Structured state — SQLite / Parquet")
    st.write("🟡 RAG — Qdrant projection")
    st.write("🟡 Relationships — Neo4j projection")

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

intelligence = st.session_state.intelligence
if intelligence is None:
    intelligence = __import__(
        "b3_agent.portfolio", fromlist=["PortfolioIntelligenceEngine"]
    ).PortfolioIntelligenceEngine().build(context)
rows = [
    {
        "Ticker": p.ticker,
        "Tipo": p.instrument_type,
        "Quantidade": p.quantity,
        "Preço": p.market_price,
        "Valor de mercado": p.market_value,
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

market_value = float(df["Valor de mercado"].fillna(0).sum())
stock_value = float(stock_df["Valor de mercado"].fillna(0).sum())
option_value = float(option_df["Valor de mercado"].fillna(0).sum())

st.title("B3 Investment Copilot")
st.caption("V4 E2E • deterministic facts • read-only")

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
    c1.metric("Options", len(option_df))
    c2.metric("Puts", int((option_df["Tipo opção"] == "PUT").sum()))
    c3.metric("Calls", int((option_df["Tipo opção"] == "CALL").sum()))
    c4.metric("Assignment capital", f"R$ {intelligence.capital_risk.assignment_capital:,.2f}")
    st.dataframe(option_df, use_container_width=True, hide_index=True)
    st.caption("Valores vêm do PortfolioContext; nenhum multiplicador ou contrato é inferido pelo dashboard.")

with tab_opportunities:
    st.subheader("Opportunities")
    opportunity_set = st.session_state.opportunities
    if opportunity_set is None:
        opportunity_set = DashboardE2EService().load(
            Path(os.environ["B3_AGENT_PORTFOLIO_FILE"])
        ).opportunities if os.getenv("B3_AGENT_PORTFOLIO_FILE", "").lower().endswith((".xlsx", ".xlsm")) else None
    c1, c2 = st.columns(2)
    c1.metric("Eligible", len(opportunity_set.ranked_opportunities) if opportunity_set else 0)
    c2.metric("Rejected", len(opportunity_set.rejected_opportunities) if opportunity_set else 0)
    st.info(
        "Nenhum input analítico de oportunidade foi carregado nesta sessão. "
        "A V4 não converte exposição de portfolio em oportunidade sem dados "
        "determinísticos upstream (market/valuation/options analysis)."
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
