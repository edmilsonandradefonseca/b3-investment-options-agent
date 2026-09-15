"""Interactive MVP dashboard for the B3 Investment Copilot."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.portfolio import PortfolioRepository


st.set_page_config(page_title="B3 Investment Copilot", page_icon="📊", layout="wide")
st.title("B3 Investment Copilot")
st.caption("MVP V0.4 • deterministic position intelligence • read-only")


def load_context():
    configured = os.getenv("B3_AGENT_PORTFOLIO_FILE", "")
    if not configured:
        return None, "B3_AGENT_PORTFOLIO_FILE não configurada."
    path = Path(configured).expanduser().resolve()
    if not path.exists():
        return None, f"Arquivo não encontrado: {path}"
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return BtgRendaVariavelLoader().load(path), None
    return PortfolioRepository(path).load(), None


context, error = load_context()
if error:
    st.warning(error)
    st.info("Defina B3_AGENT_PORTFOLIO_FILE apontando para o Excel BTG antes de iniciar o dashboard.")
    st.stop()

intelligence = PortfolioIntelligenceEngine().build(context)
positions = list(context.positions)

rows = []
for p in positions:
    rows.append(
        {
            "Position ID": p.position_id,
            "Ticker": p.ticker,
            "Tipo": p.instrument_type,
            "Quantidade": p.quantity,
            "Preço": p.market_price,
            "Valor de mercado": p.market_value,
            "Vencimento": p.expiration_date,
            "Tipo opção": p.option_type,
            "Strike": p.strike,
            "Underlying": p.underlying_ticker,
            "Multiplicador": p.contract_multiplier,
        }
    )

df = pd.DataFrame(rows)

stock_df = df[df["Tipo"] == "STOCK"]
option_df = df[df["Tipo"] == "OPTION"].copy()
option_df["Tipo opção"] = option_df["Tipo opção"].fillna("").astype(str).str.upper()

stock_value = float(stock_df["Valor de mercado"].fillna(0).sum())
option_value = float(option_df["Valor de mercado"].fillna(0).sum())
market_value = stock_value + option_value

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
with st.sidebar:
    st.header("Portfolio")
    st.write(f"**As of:** {context.as_of}")
    st.write(f"**Quality:** {context.quality_status}")
    st.write("**Source**")
    for source in context.source_refs:
        st.write(f"- {source}")
    st.divider()
    st.write("**Arquivo**")
    st.code(str(Path(os.getenv("B3_AGENT_PORTFOLIO_FILE", "")).resolve()), language="text")

# ------------------------------------------------------------------
# Overview
# ------------------------------------------------------------------
st.header("Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Valor de mercado", f"R$ {market_value:,.2f}")
c2.metric("Posições", len(df))
c3.metric("Ações", len(stock_df))
c4.metric("Opções", len(option_df))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Valor em ações", f"R$ {stock_value:,.2f}")
c2.metric("Valor em opções", f"R$ {option_value:,.2f}")
c3.metric("Puts", int((option_df["Tipo opção"] == "PUT").sum()))
c4.metric("Calls", int((option_df["Tipo opção"] == "CALL").sum()))

st.divider()

left, right = st.columns([1, 1])
with left:
    st.subheader("Distribuição por instrumento")
    distribution = (
        df.groupby("Tipo", dropna=False)["Valor de mercado"]
        .sum()
        .rename("Valor")
    )
    st.bar_chart(distribution, width="stretch")

with right:
    st.subheader("Concentração por ticker")
    concentration = (
        df.groupby("Ticker", dropna=False)["Valor de mercado"]
        .sum()
        .abs()
        .sort_values(ascending=False)
        .head(10)
    )
    st.bar_chart(concentration, width="stretch")

# ------------------------------------------------------------------
# Tabs
# ------------------------------------------------------------------
tab_portfolio, tab_options, tab_position, tab_intelligence = st.tabs(
    ["Portfolio", "Options Intelligence", "Position Analysis", "Portfolio Intelligence"]
)

with tab_portfolio:
    st.subheader("Portfolio")

    f1, f2 = st.columns([1, 2])
    with f1:
        types = ["TODOS"] + sorted(df["Tipo"].dropna().unique().tolist())
        selected_type = st.selectbox("Instrumento", types, key="portfolio_type")
    with f2:
        ticker_search = st.text_input("Ticker", placeholder="Ex.: PETR4", key="portfolio_ticker")

    view = df.copy()
    if selected_type != "TODOS":
        view = view[view["Tipo"] == selected_type]
    if ticker_search:
        search = ticker_search.strip().upper()
        view = view[
            view["Ticker"].str.upper().str.contains(search, na=False)
            | view["Underlying"].fillna("").astype(str).str.upper().str.contains(search, na=False)
        ]

    st.caption(f"Exibindo {len(view)} de {len(df)} posições.")
    st.dataframe(view.drop(columns=["Position ID"]), width="stretch", hide_index=True)

with tab_options:
    st.subheader("Options Intelligence")
    st.caption("Visão determinística das posições de opções existentes no portfolio.")

    puts = option_df[option_df["Tipo opção"] == "PUT"]
    calls = option_df[option_df["Tipo opção"] == "CALL"]
    short_options = option_df[option_df["Quantidade"] < 0]
    long_options = option_df[option_df["Quantidade"] > 0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opções", len(option_df))
    c2.metric("Puts", len(puts))
    c3.metric("Calls", len(calls))
    c4.metric("Vendidas", len(short_options))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Compradas", len(long_options))
    c2.metric("Assignment capital", f"R$ {intelligence.capital_risk.assignment_capital:,.2f}")
    c3.metric("Cash após assignment", f"R$ {intelligence.capital_risk.cash_after_assignment:,.2f}")
    c4.metric("Uncovered call shares", f"{intelligence.capital_risk.uncovered_call_shares:,.0f}")

    st.divider()

    st.markdown("#### Options Book")
    option_columns = [
        "Ticker", "Underlying", "Tipo opção", "Strike", "Vencimento",
        "Quantidade", "Preço", "Valor de mercado", "Multiplicador",
    ]
    st.dataframe(
        option_df[option_columns].sort_values(["Vencimento", "Underlying", "Strike"], na_position="last"),
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### Exposure by Underlying")
    option_underlying = (
        option_df.assign(
            Underlying=option_df["Underlying"].fillna(option_df["Ticker"])
        )
        .groupby(["Underlying", "Tipo opção"], dropna=False)
        .agg(
            Posicoes=("Ticker", "count"),
            Quantidade=("Quantidade", "sum"),
            Valor=("Valor de mercado", "sum"),
        )
        .reset_index()
        .sort_values("Valor", key=lambda s: s.abs(), ascending=False)
    )
    st.dataframe(option_underlying, width="stretch", hide_index=True)

    st.markdown("#### Expirations")
    expirations = (
        option_df.groupby("Vencimento", dropna=False)
        .agg(
            Posicoes=("Ticker", "count"),
            Valor=("Valor de mercado", "sum"),
        )
        .reset_index()
        .sort_values("Vencimento", na_position="last")
    )
    st.dataframe(expirations, width="stretch", hide_index=True)

    st.info(
        "O multiplicador e os valores apresentados são os existentes no PortfolioContext. "
        "O dashboard não infere ou altera contratos B3."
    )

with tab_position:
    st.subheader("Position Analysis")
    st.caption("Detalhamento determinístico de uma posição individual. Sem recomendação de compra ou venda.")

    assessment_by_id = {assessment.position_id: assessment for assessment in intelligence.assessments}
    position_ids = df["Position ID"].tolist()

    selected_position_id = st.selectbox(
        "Selecione a posição",
        position_ids,
        format_func=lambda pid: (
            f"{pid} — {df.loc[df['Position ID'] == pid, 'Ticker'].iloc[0]}"
            f" ({df.loc[df['Position ID'] == pid, 'Tipo'].iloc[0]})"
        ),
        key="position_analysis_id",
    )

    selected = df.loc[df["Position ID"] == selected_position_id].iloc[0]
    assessment = assessment_by_id.get(selected_position_id)

    if assessment is None:
        st.warning("Não foi encontrada avaliação determinística para esta posição.")
    else:
        st.markdown("#### Position facts")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ticker", selected["Ticker"])
        c2.metric("Instrumento", selected["Tipo"])
        c3.metric("Side", assessment.side)
        c4.metric("Lifecycle", assessment.lifecycle.state)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Quantidade", f"{selected['Quantidade']:,.2f}")
        market_price = selected["Preço"]
        c2.metric("Preço", "—" if pd.isna(market_price) else f"R$ {float(market_price):,.4f}")
        market_position_value = selected["Valor de mercado"]
        c3.metric(
            "Valor de mercado",
            "—" if pd.isna(market_position_value) else f"R$ {float(market_position_value):,.2f}",
        )
        c4.metric("Underlying", assessment.underlying_ticker)

        st.markdown("#### Instrument details")
        details = {
            "Position ID": assessment.position_id,
            "Ticker": assessment.ticker,
            "Underlying": assessment.underlying_ticker,
            "Instrument type": assessment.instrument_type,
            "Side": assessment.side,
            "Expiration": selected["Vencimento"] if not pd.isna(selected["Vencimento"]) else None,
            "Option type": selected["Tipo opção"] if not pd.isna(selected["Tipo opção"]) else None,
            "Strike": selected["Strike"] if not pd.isna(selected["Strike"]) else None,
            "Contract multiplier": selected["Multiplicador"],
        }
        st.dataframe(pd.DataFrame([details]), width="stretch", hide_index=True)

        st.markdown("#### Deterministic risk mechanics")
        risk_rows = [
            {"Metric": "Assignment capital", "Value": assessment.assignment_capital},
            {"Metric": "Deliverable shares", "Value": assessment.deliverable_shares},
            {"Metric": "Lifecycle state", "Value": assessment.lifecycle.state},
            {"Metric": "Lifecycle as of", "Value": assessment.lifecycle.as_of},
        ]
        if assessment.lifecycle.reason:
            risk_rows.append({"Metric": "Lifecycle reason", "Value": assessment.lifecycle.reason})
        st.dataframe(pd.DataFrame(risk_rows), width="stretch", hide_index=True)

        if assessment.instrument_type == "OPTION":
            option_type = (selected["Tipo opção"] or "").upper()
            if assessment.side == "SHORT" and option_type == "PUT":
                st.info("Esta posição é uma short put; o assignment capital é calculado deterministicamente a partir de quantidade, strike e multiplicador.")
            elif assessment.side == "SHORT" and option_type == "CALL":
                st.info("Esta posição é uma short call; deliverable shares representa a quantidade potencialmente entregável segundo o multiplicador armazenado.")
            else:
                st.info("A posição não gera assignment capital nem deliverable shares no modelo determinístico atual.")
        else:
            st.info("Para ações, a análise individual permanece factual e não transforma exposição em recomendação de investimento.")

with tab_intelligence:
    st.subheader("Portfolio Intelligence")
    st.write(
        "A camada de inteligência é produzida pelo mesmo engine determinístico "
        "utilizado pelo MCP; o dashboard não cria decisões de investimento."
    )

    exposures = getattr(intelligence, "exposures", ())
    exposure_rows = []
    for e in exposures:
        exposure_rows.append(
            {
                "Ticker": e.ticker,
                "Valor líquido": e.net_market_value,
                "Valor bruto": e.gross_market_value,
                "Peso": e.weight,
                "Opções": e.option_count,
                "Short options": e.short_option_count,
                "Assignment capital": e.assignment_capital,
                "Covered call contracts": e.covered_call_contracts,
                "Call coverage ratio": e.call_coverage_ratio,
            }
        )

    if exposure_rows:
        st.dataframe(pd.DataFrame(exposure_rows), width="stretch", hide_index=True)
    else:
        st.info("Nenhuma exposição calculada.")

    st.markdown("#### Capital Risk")
    risk = intelligence.capital_risk
    risk_rows = [
        {"Metric": "Cash", "Value": risk.cash},
        {"Metric": "Assignment capital", "Value": risk.assignment_capital},
        {"Metric": "Cash after assignment", "Value": risk.cash_after_assignment},
        {"Metric": "Fully cash secured", "Value": risk.fully_cash_secured},
        {"Metric": "Uncovered call shares", "Value": risk.uncovered_call_shares},
    ]
    st.dataframe(pd.DataFrame(risk_rows), width="stretch", hide_index=True)

st.divider()
st.caption(
    f"As of: {context.as_of} • Quality: {context.quality_status} • "
    f"Source: {', '.join(context.source_refs)}"
)
st.caption("Read-only MVP • No order execution • No LLM override of deterministic facts")
