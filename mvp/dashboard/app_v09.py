"""B3 Investment Copilot Dashboard V0.9 — real-data analytical dashboard.

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
import plotly.express as px
import streamlit as st

from b3_agent.options.brokerage_notes import BrokerageNoteParser
from b3_agent.options.lifecycle import OptionContract, build_option_lifecycles
from b3_agent.options.performance import OptionPerformanceEngine
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
    st.caption("V0.9 • Options BI • real data • deterministic analysis")

    btg_file = st.file_uploader(
        "BTG Portfolio",
        type=["xlsx", "xlsm"],
        key="v08_btg",
    )
    options_file = st.file_uploader(
        "Options Transactions",
        type=["xlsx", "xlsm"],
        key="v08_options",
    )
    note_files = st.file_uploader(
        "Brokerage Notes",
        type=["pdf"],
        accept_multiple_files=True,
        key="v08_notes",
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
    st.caption(
        "Power BI-style view: filters → result → cumulative performance → drill-down. "
        "Only closed/confirmed option lifecycles enter realized P&L."
    )

    registry_records = registry.list_all()
    contracts = {
        r.option_ticker: OptionContract(
            option_ticker=r.option_ticker,
            expiration_date=r.expiration_date,
            option_type=r.option_type,
            strike=r.strike,
            underlying_ticker=r.underlying_ticker,
            contract_multiplier=r.contract_multiplier,
        )
        for r in registry_records
        if r.expiration_date is not None
    }

    performances = OptionPerformanceEngine().build(
        transactions,
        contracts=contracts,
        evaluation_date=context.as_of,
    )

    # Resolve historical underlyings when current portfolio provides an
    # unambiguous B3 four-letter root match. This is an explicit inference,
    # not invented contract metadata.
    stock_root_map = {}
    for p in context.positions:
        if p.instrument_type == "OPTION":
            continue
        root = "".join(ch for ch in p.ticker.upper() if ch.isalpha())[:4]
        if root:
            stock_root_map.setdefault(root, set()).add(p.ticker.upper())

    rows = []
    for x in performances:
        underlying = x.underlying_ticker
        source = "CONTRACT_REGISTRY" if underlying else "UNRESOLVED"
        if not underlying:
            root = "".join(ch for ch in x.option_ticker.upper() if ch.isalpha())[:4]
            candidates = stock_root_map.get(root, set())
            if len(candidates) == 1:
                underlying = next(iter(candidates))
                source = "B3_ROOT_INFERENCE"
        rows.append(
            {
                "Ticker": x.option_ticker,
                "Underlying": underlying or "UNRESOLVED",
                "Underlying source": source,
                "Type": (x.option_type or "UNKNOWN").upper(),
                "Status": x.status,
                "P&L": x.realized_pnl if x.status in {"CLOSED", "EXPIRED_WORTHLESS"} else None,
                "Raw lifecycle P&L": x.realized_pnl,
                "Premium": x.premium_received,
                "Capital": x.capital_basis,
                "Return %": x.return_pct,
                "First trade": x.first_trade_date,
                "Last trade": x.last_trade_date,
                "Days": x.days_in_trade,
                "Transactions": x.transaction_count,
                "History": x.history_completeness,
                "Strike": x.strike,
            }
        )

    performance_df = pd.DataFrame(rows)

    if performance_df.empty:
        st.info("Nenhuma transação de opções persistida.")
    else:
        # Filters
        f1, f2, f3, f4 = st.columns([1.5, 1, 1, 1])
        underlyings = sorted(performance_df["Underlying"].dropna().unique())
        types = ["PUT", "CALL", "UNKNOWN"]
        statuses = sorted(performance_df["Status"].unique())
        with f1:
            selected_underlying = st.multiselect(
                "Ativo",
                underlyings,
                placeholder="Todos os ativos",
                key="v09_underlying_filter",
            )
        with f2:
            selected_type = st.multiselect(
                "Tipo",
                types,
                placeholder="PUT + CALL",
                key="v09_type_filter",
            )
        with f3:
            selected_status = st.multiselect(
                "Status",
                statuses,
                placeholder="Todos os status",
                key="v09_status_filter",
            )
        with f4:
            period = st.selectbox(
                "Período",
                ["Todo o histórico", "12 meses", "6 meses", "3 meses"],
                key="v09_period_filter",
            )

        filtered = performance_df.copy()
        if selected_underlying:
            filtered = filtered[filtered["Underlying"].isin(selected_underlying)]
        if selected_type:
            filtered = filtered[filtered["Type"].isin(selected_type)]
        if selected_status:
            filtered = filtered[filtered["Status"].isin(selected_status)]

        if period != "Todo o histórico":
            months = {"12 meses": 12, "6 meses": 6, "3 meses": 3}[period]
            cutoff = pd.Timestamp(context.as_of) - pd.DateOffset(months=months)
            dates = pd.to_datetime(filtered["Last trade"], errors="coerce")
            filtered = filtered[dates >= cutoff]

        confirmed = filtered[filtered["P&L"].notna()].copy()
        open_rows = filtered[filtered["Status"].isin({"OPEN", "EXPIRED_UNRESOLVED", "ASSIGNED", "EXERCISED"})]
        unresolved = filtered[filtered["Underlying"] == "UNRESOLVED"]

        realized_total = float(confirmed["P&L"].sum()) if not confirmed.empty else 0.0
        put_result = float(confirmed.loc[confirmed["Type"] == "PUT", "P&L"].sum()) if not confirmed.empty else 0.0
        call_result = float(confirmed.loc[confirmed["Type"] == "CALL", "P&L"].sum()) if not confirmed.empty else 0.0
        premium_total = float(filtered["Premium"].sum())
        open_count = len(open_rows)
        unresolved_count = len(unresolved)
        wins = int((confirmed["P&L"] > 0).sum()) if not confirmed.empty else 0
        losses = int((confirmed["P&L"] < 0).sum()) if not confirmed.empty else 0

        st.markdown("### Resultado das opções")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("P&L realizado", f"R$ {realized_total:,.0f}")
        m2.metric("PUT", f"R$ {put_result:,.0f}")
        m3.metric("CALL", f"R$ {call_result:,.0f}")
        m4.metric("Prêmio vendido", f"R$ {premium_total:,.0f}")
        m5.metric("Ganhos / perdas", f"{wins} / {losses}")
        m6.metric("Não concluídas", f"{open_count}")

        if unresolved_count:
            st.warning(
                f"{unresolved_count} lifecycle(s) ainda não têm underlying resolvido. "
                "Eles não são tratados como um ativo."
            )

        # Main BI chart: cumulative realized P&L by underlying.
        st.markdown("### Onde estou ganhando e onde estou perdendo?")
        if not confirmed.empty:
            by_underlying = (
                confirmed.groupby("Underlying", as_index=False)["P&L"]
                .sum()
                .sort_values("P&L")
            )
            result_chart = px.bar(
                by_underlying,
                x="P&L",
                y="Underlying",
                orientation="h",
                color="P&L",
                color_continuous_scale="RdYlGn",
                hover_data=["P&L"],
            )
            result_chart.update_layout(
                height=max(380, 32 * len(by_underlying)),
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                xaxis_title="P&L realizado (R$)",
                yaxis_title="",
            )
            st.plotly_chart(result_chart, use_container_width=True)
        else:
            st.info("Não há ciclos encerrados/confirmados para o filtro selecionado.")

        # Cumulative portfolio performance.
        st.markdown("### P&L acumulado")
        if not confirmed.empty:
            cumulative = confirmed.dropna(subset=["Last trade"]).copy()
            cumulative["Date"] = pd.to_datetime(cumulative["Last trade"])
            cumulative = cumulative.sort_values(["Date", "Ticker"])
            cumulative["P&L acumulado"] = cumulative["P&L"].cumsum()
            cumulative_chart = px.line(
                cumulative,
                x="Date",
                y="P&L acumulado",
                markers=True,
                hover_data=["Ticker", "Underlying", "Type", "P&L", "Status"],
            )
            cumulative_chart.update_layout(
                height=380,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Data de fechamento",
                yaxis_title="P&L acumulado (R$)",
            )
            st.plotly_chart(cumulative_chart, use_container_width=True)

        # Monthly view is secondary: it explains the journey, not the total result.
        st.markdown("### Resultado mensal × acumulado")
        if not confirmed.empty:
            monthly = confirmed.dropna(subset=["Last trade"]).copy()
            monthly["Month"] = pd.to_datetime(monthly["Last trade"]).dt.to_period("M").astype(str)
            monthly = monthly.groupby("Month", as_index=False)["P&L"].sum()
            monthly["P&L acumulado"] = monthly["P&L"].cumsum()

            monthly_chart = px.bar(
                monthly,
                x="Month",
                y="P&L",
                hover_data=["P&L"],
            )
            monthly_chart.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Mês",
                yaxis_title="P&L realizado (R$)",
            )
            st.plotly_chart(monthly_chart, use_container_width=True)

        # PUT vs CALL by underlying.
        st.markdown("### PUT × CALL por papel")
        if not confirmed.empty:
            pc = (
                confirmed.groupby(["Underlying", "Type"], as_index=False)["P&L"]
                .sum()
            )
            pc_chart = px.bar(
                pc,
                x="Underlying",
                y="P&L",
                color="Type",
                barmode="group",
                hover_data=["P&L"],
            )
            pc_chart.update_layout(
                height=380,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Ativo",
                yaxis_title="P&L realizado (R$)",
            )
            st.plotly_chart(pc_chart, use_container_width=True)

        # Ranking table.
        st.markdown("### Performance acumulada por papel")
        if not confirmed.empty:
            ranking = (
                confirmed.groupby("Underlying", as_index=False)
                .agg(
                    PnL=("P&L", "sum"),
                    Operations=("Ticker", "count"),
                    Premium=("Premium", "sum"),
                )
                .sort_values("PnL", ascending=False)
            )
            st.dataframe(
                ranking,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "PnL": st.column_config.NumberColumn("P&L", format="R$ %.2f"),
                    "Premium": st.column_config.NumberColumn("Prêmio", format="R$ %.2f"),
                },
            )

        # Drill-down: selected underlying -> cumulative curve -> contracts -> trades.
        st.markdown("### Drill-down")
        available = sorted(filtered["Underlying"].unique())
        if available:
            selected = st.selectbox(
                "Escolha um papel",
                available,
                key="v09_drilldown",
            )
            detail = filtered[filtered["Underlying"] == selected].copy()
            detail_confirmed = detail[detail["P&L"].notna()].copy()

            d1, d2, d3, d4, d5 = st.columns(5)
            d1.metric("P&L acumulado", f"R$ {detail_confirmed['P&L'].sum():,.0f}" if not detail_confirmed.empty else "R$ 0")
            d2.metric("PUT", f"R$ {detail_confirmed.loc[detail_confirmed['Type']=='PUT','P&L'].sum():,.0f}" if not detail_confirmed.empty else "R$ 0")
            d3.metric("CALL", f"R$ {detail_confirmed.loc[detail_confirmed['Type']=='CALL','P&L'].sum():,.0f}" if not detail_confirmed.empty else "R$ 0")
            d4.metric("Operações", len(detail))
            d5.metric("Abertas", int(detail["Status"].isin({"OPEN", "EXPIRED_UNRESOLVED", "ASSIGNED", "EXERCISED"}).sum()))

            if not detail_confirmed.empty:
                curve = detail_confirmed.dropna(subset=["Last trade"]).copy()
                curve["Date"] = pd.to_datetime(curve["Last trade"])
                curve = curve.sort_values(["Date", "Ticker"])
                curve["P&L acumulado"] = curve["P&L"].cumsum()
                detail_curve = px.line(
                    curve,
                    x="Date",
                    y="P&L acumulado",
                    markers=True,
                    hover_data=["Ticker", "Type", "P&L", "Premium", "Days", "Status"],
                )
                detail_curve.update_layout(
                    height=350,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_title="Data",
                    yaxis_title="P&L acumulado (R$)",
                )
                st.plotly_chart(detail_curve, use_container_width=True)

            st.dataframe(
                detail.sort_values(["Last trade", "Ticker"]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "P&L": st.column_config.NumberColumn("P&L", format="R$ %.2f"),
                    "Raw lifecycle P&L": st.column_config.NumberColumn("P&L bruto do lifecycle", format="R$ %.2f"),
                    "Premium": st.column_config.NumberColumn("Prêmio", format="R$ %.2f"),
                    "Capital": st.column_config.NumberColumn("Capital", format="R$ %.2f"),
                    "Return %": st.column_config.NumberColumn("Retorno", format="%.2f%%"),
                },
            )

        # Data quality is visible, but kept below the analytical view.
        with st.expander("Qualidade e cobertura dos dados"):
            st.write(
                f"**{len(performances)} lifecycles** reconstruídos • "
                f"**{len(confirmed)}** confirmados como resultado realizado • "
                f"**{open_count}** ainda abertos/não concluídos • "
                f"**{unresolved_count}** sem underlying resolvido."
            )
            st.caption(
                "P&L realizado inclui somente CLOSED e EXPIRED_WORTHLESS. "
                "OPEN, ASSIGNED, EXERCISED e EXPIRED_UNRESOLVED ficam fora do resultado realizado."
            )

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
