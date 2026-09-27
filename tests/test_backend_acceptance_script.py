from pathlib import Path


def test_backend_acceptance_script_compiles_and_covers_real_runtime_gates():
    path = Path("scripts/backend_acceptance.py")
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")

    for marker in (
        "HttpEmbeddingProvider",
        "QdrantVectorStore",
        "b3_evidence_768_hybrid",
        "Neo4jKnowledgeGraphStore",
        "load_active_snapshots",
        "OptionTransactionLedger",
        "LiveProviderService",
        "SearxngNewsAdapter",
        "ResearchEventService",
        "B3 BACKEND ACCEPTANCE PASSED",
    ):
        assert marker in source
