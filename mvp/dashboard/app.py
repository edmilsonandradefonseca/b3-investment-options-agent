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
st.caption("MVP • deterministic portfolio intelligence • read-only")


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
            "Ticker": p.ticker,
            "Tipo": p.instrument_type,
            "Quantidade": p.quantity,
            "Valor de mercado": p.market_value,
            "Preço": p.market_price,
            "Vencimento": getattr(p, "expiration_date", None),
            "Tipo opção": getattr(p, "option_type", None),
            "Strike": getattr(p, "strike", None),
        }
    )

df = pd.DataFrame(rows)

stock_value = float(df.loc[df["Tipo"] == "STOCK", "Valor de mercado"].fillna(0).sum())
option_value = float(df.loc[df["Tipo"] == "OPTION", "Valor de mercado"].fillna(0).sum())
market_value = stock_value + option_value

c1, c2, c3, c4 = st.columns(4)
c1.metric("Posições", len(df))
c2.metric("Valor de mercado", f"R$ {market_value:,.2f}")
c3.metric("Ações", f"R$ {stock_value:,.2f}")
c4.metric("Opções", f"R$ {option_value:,.2f}")

st.divider()

left, right = st.columns([1.6, 1])
with left:
    st.subheader("Portfolio")
    types = ["TODOS"] + sorted(df["Tipo"].dropna().unique().tolist())
    selected = st.selectbox("Instrumento", types)
    view = df if selected == "TODOS" else df[df["Tipo"] == selected]
    st.dataframe(view, use_container_width=True, hide_index=True)

with right:
    st.subheader("Distribuição")
    distribution = (
        df.groupby("Tipo", dropna=False)["Valor de mercado"]
        .sum()
        .reset_index()
        .rename(columns={"Valor de mercado": "Valor"})
    )
    st.bar_chart(distribution.set_index("Tipo"))

st.divider()
st.subheader("Portfolio Intelligence")
st.write(
    "A camada de inteligência abaixo é produzida pelo mesmo engine determinístico "
    "utilizado pelo MCP; o dashboard não cria decisões de investimento."
)

with st.expander("Exposures", expanded=True):
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
                "Assignment capital": e.assignment_capital,
                "Covered calls": e.covered_call_count,
            }
        )
    if exposure_rows:
        st.dataframe(pd.DataFrame(exposure_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma exposição calculada.")

st.caption(f"As of: {context.as_of} • Quality: {context.quality_status} • Source: {', '.join(context.source_refs)}")
