from datetime import datetime, timezone

from b3_agent.repositories.provenance import ProvenanceRepository
from b3_agent.schemas.provenance import (
    Claim, ClaimEvidenceDirection, ClaimEvidenceLink, SourceDocument,
)
from b3_agent.storage.sqlite import SQLiteStore


NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def test_source_claim_evidence_provenance_roundtrip(tmp_path):
    store = SQLiteStore(tmp_path / "b3.db")
    store.initialize()
    repo = ProvenanceRepository(store)
    repo.save_document(SourceDocument(
        document_id="DOC-1", source="provider", title="PETR4 report",
        retrieved_at=NOW, published_at=NOW, version=1,
    ))
    repo.save_claim(Claim(
        claim_id="CLM-1", statement="A material claim.", created_at=NOW,
    ))
    repo.link(ClaimEvidenceLink(
        claim_id="CLM-1", evidence_id="EV-1", document_id="DOC-1",
        direction=ClaimEvidenceDirection.SUPPORTS, observed_at=NOW, confidence=0.9,
    ))
    repo.link(ClaimEvidenceLink(
        claim_id="CLM-1", evidence_id="EV-2", document_id="DOC-1",
        direction=ClaimEvidenceDirection.CONTRADICTS, observed_at=NOW, confidence=0.7,
    ))
    links = repo.evidence_for_claim("CLM-1")
    assert [item.direction for item in links] == [
        ClaimEvidenceDirection.SUPPORTS, ClaimEvidenceDirection.CONTRADICTS
    ]
    assert {item.evidence_id for item in links} == {"EV-1", "EV-2"}
