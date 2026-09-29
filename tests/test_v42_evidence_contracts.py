from datetime import datetime, timezone

import pytest

from b3_agent.intelligence import AcquisitionStatus, EvidenceConclusion, ProviderResultEnvelope
from b3_agent.knowledge.evidence import EvidenceMetadata


NOW = datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc)


def test_provider_result_envelope_accepts_v42_coverage_state():
    result = ProviderResultEnvelope(
        provider="searxng",
        started_at=NOW,
        completed_at=NOW,
        status=AcquisitionStatus.PARTIAL,
        raw_result_count=60,
        normalized_result_count=8,
        warnings=("bing news: parsing error",),
        fallback_used=False,
        coverage_metadata={"evidence_conclusion": EvidenceConclusion.NO_MATERIAL_FOUND.value},
    )

    assert result.status == AcquisitionStatus.PARTIAL
    assert result.coverage_metadata["evidence_conclusion"] == "NO_MATERIAL_FOUND"


def test_evidence_metadata_preserves_v42_authority_and_pit_dimensions():
    metadata = EvidenceMetadata(
        document_id="DOC-1",
        source="CVM_RAD",
        published_at=NOW,
        retrieved_at=NOW,
        ticker_refs=("petr4", "PETR3"),
        issuer_ref="issuer:petrobras",
        cvm_code="9512",
        provider_record_id="rad:123",
        source_class="OFFICIAL_REGULATORY",
        authority_tier=0,
        discovery_channel="CVM_RAD",
        transport_reliability="DOCUMENTED_OFFICIAL",
        reference_at=NOW,
        first_seen_at=NOW,
        observed_at=NOW,
        source_status="LIBERADO",
        acquisition_status="SUCCESS",
        pit_status="OBSERVED_LIVE",
        materiality="MATERIAL",
        materiality_reason="OFFICIAL_FATO_RELEVANTE",
        materiality_policy_version="v4.2",
    )

    assert metadata.ticker_refs == ("PETR4", "PETR3")
    assert metadata.authority_tier == 0
    assert metadata.pit_status == "OBSERVED_LIVE"


def test_evidence_metadata_rejects_invalid_authority_tier():
    with pytest.raises(ValueError, match="authority_tier"):
        EvidenceMetadata(
            document_id="DOC-1",
            source="web",
            published_at=NOW,
            retrieved_at=NOW,
            authority_tier=4,
        )
