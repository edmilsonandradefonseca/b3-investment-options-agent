"""B3 Investment Copilot Dashboard V0.6 — lightweight UX prototype.

This is intentionally a shallow iteration for real-user feedback.
It reuses deterministic domain engines and loaders; it does not implement
new investment logic, Neo4j ingestion, or LLM orchestration.
"""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from b3_agent.config import settings
from b3_agent.dashboard_e2e import DashboardE2EService
from b3_agent.options.brokerage_notes import BrokerageNoteParser
from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.portfolio import PortfolioRepository

st.set_page_config(page_title="B3 Investment Copilot", page_icon="📊", layout="wide")

MAX_DIRECT_PDFS = 10
MAX_ARCHIVE_PDFS = 250
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 100 * 1024 * 1024

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
    uploaded_file.seek(0)
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    while True:
        chunk = uploaded_file.read(1024 * 1024)
        if not chunk:
            break
        handle.write(chunk)
    handle.close()
    uploaded_file.seek(0)
    return Path(handle.name)


def _parse_and_append_note(
    note_path: Path,
    display_name: str,
    ledger: OptionTransactionLedger,
) -> tuple[int, int, str | None]:
    try:
        transactions = BrokerageNoteParser().parse(note_path)
        return len(transactions), ledger.append(transactions), None
    except Exception as exc:
        return 0, 0, f"{display_name}: {exc}"


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
    "strategy_comparisons": (),
    "stress_results": (),
    "market_regime": None,
    "factor_study": None,
    "factor_walk_forward": (),
    "btg_status": "Not loaded",
    "options_status": "No brokerage notes loaded",
    "load_error": None,
}.items():
    st.session_state.setdefault(key, default)

with st.sidebar:
    st.header("DATA & COPILOT")
    st.caption("V4 E2E • read-only")

    st.markdown("#### Current portfolio")
    btg_file = st.file_uploader(
        "BTG Portfolio",
        type=["xlsx", "xlsm"],
        key="v06_btg",
        help="Somente Renda Variavel > Posição > Ações e Posição > Opções são importadas.",
    )

    if st.button("📥 LOAD BTG PORTFOLIO", type="primary", use_container_width=True):
        st.session_state.load_error = None
        if not btg_file:
            st.session_state.load_error = "Selecione o arquivo Excel do BTG."
        else:
            portfolio_path = _temp_path(btg_file)
            try:
                snapshot = DashboardE2EService().load(portfolio_path)
                st.session_state.context = snapshot.portfolio
                st.session_state.intelligence = snapshot.portfolio_intelligence
                st.session_state.opportunities = snapshot.opportunities
                st.session_state.strategy_comparisons = snapshot.strategy_comparisons
                st.session_state.stress_results = snapshot.stress_results
                st.session_state.market_regime = snapshot.market_regime
                st.session_state.factor_study = snapshot.factor_study
                st.session_state.factor_walk_forward = snapshot.factor_walk_forward
                st.session_state.transactions = OptionTransactionLedger(
                    settings.data_dir / "options.sqlite3"
                ).list_all()
                st.session_state.btg_status = (
                    f"✓ Loaded — {len(snapshot.portfolio.positions)} positions"
                )
            except Exception as exc:
                st.session_state.btg_status = "✗ Load failed"
                st.session_state.load_error = f"BTG load: {exc}"
            finally:
                portfolio_path.unlink(missing_ok=True)

    st.markdown("#### Brokerage notes")
    st.caption(
        "Para poucos arquivos, envie até 10 PDFs por lote. "
        "Para histórico grande, compacte as notas em um único ZIP."
    )
    direct_pdfs = st.file_uploader(
        "PDFs de notas",
        type=["pdf"],
        accept_multiple_files=True,
        key="v06_brokerage_pdfs",
        help=f"Até {MAX_DIRECT_PDFS} PDFs por lote.",
    )
    archive_file = st.file_uploader(
        "ZIP de notas",
        type=["zip"],
        accept_multiple_files=False,
        key="v06_brokerage_zip",
        help=(
            f"Um único ZIP por lote, até {MAX_ARCHIVE_PDFS} PDFs e "
            "100 MB descompactados."
        ),
    )

    if st.button("🧾 IMPORT BROKERAGE NOTES", use_container_width=True):
        st.session_state.load_error = None
        if not direct_pdfs and archive_file is None:
            st.session_state.load_error = "Selecione PDFs ou um ZIP com notas de corretagem."
        elif direct_pdfs and archive_file is not None:
            st.session_state.load_error = (
                "Envie PDFs OU um único ZIP por lote, não os dois formatos juntos."
            )
        elif len(direct_pdfs) > MAX_DIRECT_PDFS:
            st.session_state.load_error = (
                f"Selecione no máximo {MAX_DIRECT_PDFS} PDFs por lote. "
                "Para muitas notas, use um arquivo ZIP."
            )
        else:
                ledger = OptionTransactionLedger(settings.data_dir / "options.sqlite3")
                inserted = 0
                parsed = 0
                failures = []
                processed_files = 0

                progress = st.progress(0.0, text="Preparando notas...")
                status = st.empty()

                if archive_file is not None:
                    archive_path = _temp_path(archive_file)
                    try:
                        with zipfile.ZipFile(archive_path) as archive:
                            members = [
                                info for info in archive.infolist()
                                if not info.is_dir() and info.filename.lower().endswith(".pdf")
                            ]
                            if not members:
                                raise ValueError("ZIP não contém arquivos PDF.")
                            if len(members) > MAX_ARCHIVE_PDFS:
                                raise ValueError(
                                    f"ZIP contém {len(members)} PDFs; máximo suportado por lote é "
                                    f"{MAX_ARCHIVE_PDFS}."
                                )
                            total_uncompressed = sum(info.file_size for info in members)
                            if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                                raise ValueError(
                                    "ZIP excede o limite de 100 MB descompactados."
                                )

                            total_files = len(members)
                            for index, info in enumerate(members, start=1):
                                status.write(f"Processando {index}/{total_files}: {Path(info.filename).name}")
                                suffix = Path(info.filename).suffix or ".pdf"
                                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                                    with archive.open(info) as source:
                                        while True:
                                            chunk = source.read(1024 * 1024)
                                            if not chunk:
                                                break
                                            handle.write(chunk)
                                    note_path = Path(handle.name)
                                try:
                                    parsed_count, inserted_count, error = _parse_and_append_note(
                                        note_path, info.filename, ledger
                                    )
                                    parsed += parsed_count
                                    inserted += inserted_count
                                    processed_files += 1
                                    if error:
                                        failures.append(error)
                                finally:
                                    note_path.unlink(missing_ok=True)
                                progress.progress(
                                    index / total_files,
                                    text=f"Processadas {index}/{total_files} notas",
                                )
                    except Exception as exc:
                        failures.append(f"{archive_file.name}: {exc}")
                    finally:
                        archive_path.unlink(missing_ok=True)
                else:
                    total_files = len(direct_pdfs)
                    for index, uploaded in enumerate(direct_pdfs, start=1):
                        status.write(f"Processando {index}/{total_files}: {uploaded.name}")
                        note_path = _temp_path(uploaded)
                        try:
                            parsed_count, inserted_count, error = _parse_and_append_note(
                                note_path, uploaded.name, ledger
                            )
                            parsed += parsed_count
                            inserted += inserted_count
                            processed_files += 1
                            if error:
                                failures.append(error)
                        finally:
                            note_path.unlink(missing_ok=True)
                        progress.progress(
                            index / total_files,
                            text=f"Processadas {index}/{total_files} notas",
                        )

                st.session_state.transactions = ledger.list_all()
                st.session_state.options_status = (
                    f"✓ Ledger — {len(st.session_state.transactions)} transactions "
                    f"({inserted} new / {parsed} parsed / {processed_files} files)"
                )
                progress.empty()
                status.empty()

                if failures:
                    preview = failures[:10]
                    extra = len(failures) - len(preview)
                    message = " | ".join(preview)
                    if extra > 0:
                        message += f" | ... e mais {extra} erro(s)"
                    st.session_state.load_error = message
                else:
                    st.success(
                        f"Lote concluído: {processed_files} arquivo(s), "
                        f"{parsed} operações lidas, {inserted} novas."
                    )

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
    intelligence = PortfolioIntelligenceEngine().build(context)
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
tab_portfolio, tab_options, tab_opportunities, tab_intelligence, tab_decision, tab_factors = st.tabs(
    ["Portfolio", "Options Intelligence", "Opportunities", "Portfolio Intelligence", "Decision Context", "Factor Intelligence"]
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
    risk1, risk2 = st.columns(2)
    risk1.metric(
        "Uncovered call shares",
        f"{intelligence.capital_risk.uncovered_call_shares:,.0f}",
    )
    risk2.metric(
        "Cash secured",
        "Unknown" if intelligence.capital_risk.fully_cash_secured is None else ("Yes" if intelligence.capital_risk.fully_cash_secured else "No"),
    )
    st.dataframe(option_df, use_container_width=True, hide_index=True)
    expiration_rows = [
        {
            "Vencimento": item.expiration_date,
            "Opções": item.option_count,
            "Short puts": item.short_put_count,
            "Short calls": item.short_call_count,
            "Capital assignment": item.assignment_capital,
            "Ações entregáveis": item.deliverable_shares,
        }
        for item in intelligence.expiration_risk
    ]
    if expiration_rows:
        st.markdown("#### Risk by expiration")
        st.dataframe(pd.DataFrame(expiration_rows), use_container_width=True, hide_index=True)
    transactions = st.session_state.transactions
    if not transactions:
        ledger_path = settings.data_dir / "options.sqlite3"
        if ledger_path.exists():
            transactions = OptionTransactionLedger(ledger_path).list_all()
            st.session_state.transactions = transactions

    if transactions:
        st.markdown("#### Histórico de compra e venda — notas de corretagem")
        tx_rows = [
            {
                "Data": item.as_of,
                "Opção": item.option_ticker,
                "Lado": item.side,
                "Quantidade": item.absolute_quantity,
                "Preço executado": item.execution_price,
                "Valor total": item.total_amount,
                "Nota": item.note_number,
                "Corretora": item.broker,
            }
            for item in transactions
        ]
        st.dataframe(
            pd.DataFrame(tx_rows).sort_values(["Data", "Opção"], ascending=[False, True]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhuma nota de corretagem importada. O preço histórico de compra/venda ainda não está disponível.")

    st.caption(
        "BTG Portfolio é autoritativo para a posição atual; notas de corretagem "
        "são histórico append-only para preços executados e reconstrução das operações."
    )

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
    if opportunity_set and opportunity_set.ranked_opportunities:
        opportunity_rows = [
            {
                "Ticker": item.ticker,
                "Ação": item.action,
                "Atratividade": item.attractiveness,
                "Retorno esperado": item.expected_return,
                "Capital requerido": item.capital_requirement,
                "Valuation ref": item.valuation_range_ref,
                "Options ref": item.options_analysis_ref,
                "Quant ref": item.quant_features_ref,
                "Fontes": ", ".join(item.source_refs),
            }
            for item in opportunity_set.ranked_opportunities
        ]
        st.dataframe(pd.DataFrame(opportunity_rows), use_container_width=True, hide_index=True)
        st.caption(
            f"Ranking policy {opportunity_set.ranking_policy_version} • "
            f"Quality {opportunity_set.quality_status}"
        )
    else:
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
            "Call coverage": e.call_coverage_ratio,
        }
        for e in getattr(intelligence, "exposures", ())
    ]
    if exposures:
        exposure_df = pd.DataFrame(exposures)
        st.markdown("#### Economic exposure")
        st.dataframe(exposure_df, use_container_width=True, hide_index=True)
        concentrated = exposure_df.sort_values("Peso", ascending=False).head(5)
        st.markdown("#### Top 5 concentration")
        st.dataframe(
            concentrated[["Ticker", "Valor líquido", "Peso", "Assignment capital", "Call coverage"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhuma exposição calculada.")

with tab_decision:
    st.subheader("Decision Context")
    st.caption("UC-04 / UC-05 • explicit assumptions • no hidden ranking")
    regime = st.session_state.market_regime
    if regime is not None:
        st.markdown("#### Market regime")
        st.dataframe(
            pd.DataFrame([
                {"Dimensão": item.name.value, "Estado": item.label, "Score": item.score}
                for item in regime.dimensions
            ]),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            f"{regime.classifier_version} • confidence={regime.confidence:.2f} • "
            f"sources={', '.join(regime.source_refs)}"
        )
    else:
        st.info("Nenhum FeatureSnapshot validado foi carregado para classificação de regime.")

    comparisons = st.session_state.strategy_comparisons
    if comparisons:
        st.markdown("#### Strategy comparisons")
        rows = []
        for item in comparisons:
            left, right = item.alternatives
            rows.append({
                "Left": left.label, "Right": right.label,
                "Capital Δ": item.capital_delta,
                "Expected return Δ": item.expected_return_delta,
                "Max loss Δ": item.max_loss_delta,
                "Liquidity Δ": item.liquidity_delta,
                "Quality": item.quality_status,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Todos os deltas são right-minus-left; nenhuma alternativa é escolhida automaticamente.")
    else:
        st.info("Nenhum par de estratégias explícito foi carregado.")

    stresses = st.session_state.stress_results
    if stresses:
        st.markdown("#### Scenario stress")
        st.dataframe(
            pd.DataFrame([
                {
                    "Scenario": item.scenario_id,
                    "Base": item.base_portfolio_value,
                    "Stressed": item.stressed_portfolio_value,
                    "P&L": item.portfolio_pnl,
                    "Return": item.portfolio_return,
                    "Gross exposure": item.gross_exposure,
                    "Max concentration": item.max_concentration,
                    "Quality": item.quality_status,
                }
                for item in stresses
            ]),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Choques são inputs explícitos; o dashboard não infere previsão nem repricing de opções.")
    else:
        st.info("Nenhum cenário explícito foi carregado.")

with tab_factors:
    st.subheader("Factor Intelligence")
    st.caption("UC-06 • statistical association only • no causal claim")
    factor_study = st.session_state.factor_study
    if factor_study is None:
        st.info("Nenhuma série de fatores validada foi carregada.")
    else:
        st.dataframe(pd.DataFrame([{
            "Factor": item.factor_id,
            "N": item.sample_size,
            "Train corr": item.train_correlation,
            "Holdout corr": item.holdout_correlation,
            "Adjusted p": item.adjusted_p_value,
            "Direction stable": item.direction_stable,
            "Significant": item.statistically_significant,
            "Quality": item.quality_status,
        } for item in factor_study.results]), use_container_width=True, hide_index=True)
        st.caption(f"Multiple testing: {factor_study.correction_method} • alpha={factor_study.alpha:.2f}")
        walk = st.session_state.factor_walk_forward
        if walk:
            st.markdown("#### Walk-forward robustness")
            st.dataframe(pd.DataFrame([{
                "Factor": item.factor_id,
                "Folds": len(item.folds),
                "Stable fold ratio": item.stable_fold_ratio,
                "Median test corr": item.median_test_correlation,
                "Quality": item.quality_status,
            } for item in walk]), use_container_width=True, hide_index=True)
        st.warning("Significância e correlação não demonstram causalidade nem constituem recomendação de investimento.")

st.divider()
st.caption(
    f"As of: {context.as_of} • Quality: {context.quality_status} • "
    f"Sources: {', '.join(context.source_refs)}"
)
st.caption("Prototype only • no order execution • no LLM override of deterministic facts")
