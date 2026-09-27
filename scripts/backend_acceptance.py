#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from b3_agent.config import settings
from b3_agent.knowledge.embeddings import HttpEmbeddingProvider
from b3_agent.knowledge.neo4j_store import Neo4jKnowledgeGraphStore
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.knowledge.runtime_projection import RuntimeProjectionService
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.providers.brapi.fundamentals import BrapiFundamentalsAdapter
from b3_agent.providers.bcb_sgs import BcbSgsAdapter
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.research_events import ResearchEventService


QDRANT_COLLECTION = "b3_evidence_768_hybrid"
EMBEDDING_DIMENSIONS = 768


def _load_shared_env() -> None:
    env_path = Path(
        os.getenv("B3_SHARED_PLATFORM_ENV", "/opt/joao-runtime/joao.env")
    )
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required for backend acceptance")
    return value


def run_acceptance(*, ticker: str = "PETR4") -> dict[str, object]:
    _load_shared_env()

    embedding_url = os.getenv("B3_EMBEDDING_URL", "http://127.0.0.1:8093")
    qdrant_url = os.getenv("B3_QDRANT_URL", "http://127.0.0.1:6333")
    neo4j_uri = os.getenv("B3_NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_user = os.getenv("B3_NEO4J_USER", "neo4j")
    searxng_url = os.getenv("B3_SEARXNG_URL", "http://127.0.0.1:8080")
    neo4j_password = _require("NEO4J_PASSWORD")

    normalized_ticker = ticker.upper().strip()
    if not normalized_ticker:
        raise ValueError("ticker must not be empty")

    print("===== B3 BACKEND ACCEPTANCE =====")

    embeddings = HttpEmbeddingProvider(
        base_url=embedding_url,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    vector = embeddings.embed(("B3 backend production acceptance",))[0]
    if len(vector.values) != EMBEDDING_DIMENSIONS:
        raise RuntimeError("embedding dimension mismatch")
    print(f"EMBEDDING OK dimensions={len(vector.values)} model={vector.model}")

    qdrant_client = QdrantClient(url=qdrant_url)
    qdrant_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=QDRANT_COLLECTION,
        vector_size=EMBEDDING_DIMENSIONS,
        hybrid=True,
    )
    qdrant_count = qdrant_store.count()
    print(
        f"QDRANT OK collection={QDRANT_COLLECTION} "
        f"mode=hybrid dense=768 sparse=yes count={qdrant_count}"
    )

    driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password),
    )
    driver.verify_connectivity()
    graph = Neo4jKnowledgeGraphStore(driver)
    neo4j_entities_before = graph.count_entities()
    neo4j_relations_before = graph.count_relations()
    print(
        f"NEO4J OK B3Entity entities={neo4j_entities_before} "
        f"relations={neo4j_relations_before}"
    )

    projection = RuntimeProjectionService(
        graph=graph,
        vector_store=qdrant_store,
        embeddings=embeddings,
    )

    snapshots = load_active_snapshots(settings.data_dir)
    portfolio = snapshots.get("portfolio_context")
    if portfolio is None:
        print("PORTFOLIO WARNING no active BTG portfolio.xlsx")
        portfolio_positions = 0
    else:
        portfolio_positions = len(portfolio.positions)
        portfolio_projection = projection.project_portfolio(portfolio)
        print(
            f"PORTFOLIO OK positions={portfolio_positions} "
            f"as_of={portfolio.as_of.isoformat()} cash_known={portfolio.cash_is_known} "
            f"projected_entities={portfolio_projection['entities']} "
            f"projected_relations={portfolio_projection['relations']}"
        )

    ledger_path = settings.data_dir / "options.sqlite3"
    if ledger_path.is_file():
        ledger_count = len(OptionTransactionLedger(ledger_path).list_all())
        print(f"OPTION LEDGER OK transactions={ledger_count}")
    else:
        ledger_count = 0
        print("OPTION LEDGER WARNING no options.sqlite3 yet")

    live = LiveProviderService().load(normalized_ticker)
    print(
        f"LIVE PROVIDERS OK ticker={live.ticker} "
        f"market={len(live.market_records)} "
        f"contracts={len(live.option_contracts)} "
        f"quotes={len(live.option_quotes)} "
        f"puts={len(live.options_analysis.puts)} "
        f"calls={len(live.options_analysis.calls)}"
    )

    brapi_fundamentals = BrapiFundamentalsAdapter()
    fundamental_records = brapi_fundamentals.get_financial_data(normalized_ticker)
    dividend_records = brapi_fundamentals.get_dividends(normalized_ticker)
    print(
        f"FUNDAMENTALS OK ticker={normalized_ticker} "
        f"metrics={len(fundamental_records)} dividends={len(dividend_records)}"
    )

    macro_end = datetime.now(timezone.utc).date()
    macro_start = macro_end - timedelta(days=90)
    macro_snapshot = BcbSgsAdapter().get_core_snapshot(
        start=macro_start,
        end=macro_end,
    )
    print(
        "MACRO OK "
        + " ".join(
            f"{name}={item.value}"
            for name, item in sorted(macro_snapshot.items())
        )
    )

    news_records = SearxngNewsAdapter(base_url=searxng_url).search(
        normalized_ticker,
        limit=5,
    )
    research = ResearchEventService().build(
        news_records,
        as_of=datetime.now(timezone.utc),
    )
    research_projection = projection.project_research(research)
    print(
        f"RESEARCH OK records={len(news_records)} "
        f"pit_events={len(research.events)} "
        f"future_excluded={research.excluded_future_count} "
        f"qdrant_chunks={research_projection['qdrant_chunks']}"
    )

    qdrant_count = qdrant_store.count()
    neo4j_entities = graph.count_entities()
    neo4j_relations = graph.count_relations()
    driver.close()

    if research.events and qdrant_count < 1:
        raise RuntimeError("Qdrant projection remained empty after live research projection")
    if research.events and neo4j_entities < 2:
        raise RuntimeError("Neo4j projection remained empty after live research projection")

    print(
        f"PROJECTIONS OK qdrant_count={qdrant_count} "
        f"neo4j_entities={neo4j_entities} neo4j_relations={neo4j_relations}"
    )
    print("===== B3 BACKEND ACCEPTANCE PASSED =====")
    return {
        "ticker": normalized_ticker,
        "embedding_dimensions": len(vector.values),
        "qdrant_count": qdrant_count,
        "neo4j_entities": neo4j_entities,
        "neo4j_relations": neo4j_relations,
        "portfolio_positions": portfolio_positions,
        "option_ledger_transactions": ledger_count,
        "market_records": len(live.market_records),
        "option_contracts": len(live.option_contracts),
        "option_quotes": len(live.option_quotes),
        "fundamental_metrics": len(fundamental_records),
        "dividend_records": len(dividend_records),
        "macro_indicators": len(macro_snapshot),
        "research_events": len(research.events),
    }


if __name__ == "__main__":
    run_acceptance(ticker=os.getenv("B3_ACCEPTANCE_TICKER", "PETR4"))
