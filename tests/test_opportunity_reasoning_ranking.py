from b3_agent.agents.reasoning import _parse_assessments


def assessment(
    ticker,
    *,
    status,
    rank=0,
    refs=(),
    support=(),
):
    return {
        "alternative_id": ticker,
        "opportunity_status": status,
        "priority_rank": rank,
        "supporting_evidence": list(support),
        "contradicting_evidence": [],
        "decision_implications": [],
        "unknowns": [],
        "evidence_refs": list(refs),
    }


def test_only_source_backed_qualified_opportunities_are_ranked():
    result = _parse_assessments(
        [
            assessment(
                "PETR4",
                status="QUALIFIED_OPPORTUNITY",
                rank=1,
                refs=("news:petr4:1",),
                support=("Catalisador datado confirmado.",),
            ),
            assessment("VALE3", status="MONITOR"),
            assessment("ABEV3", status="INSUFFICIENT_EVIDENCE"),
        ],
        ["PETR4", "VALE3", "ABEV3"],
        allowed_source_refs={"news:petr4:1"},
    )

    assert [(item.alternative_id, item.opportunity_status, item.priority_rank) for item in result] == [
        ("PETR4", "QUALIFIED_OPPORTUNITY", 1),
        ("VALE3", "MONITOR", 0),
        ("ABEV3", "INSUFFICIENT_EVIDENCE", 0),
    ]


def test_unprovided_source_reference_demotes_rank_to_insufficient_evidence():
    result = _parse_assessments(
        [
            assessment(
                "PETR4",
                status="QUALIFIED_OPPORTUNITY",
                rank=1,
                refs=("news:not-in-context",),
                support=("Tese com referência não fornecida ao agente.",),
            )
        ],
        ["PETR4"],
        allowed_source_refs={"news:petr4:1"},
    )

    assert result[0].priority_rank == 0
    assert result[0].opportunity_status == "INSUFFICIENT_EVIDENCE"
    assert any("não consta no contexto" in item for item in result[0].unknowns)


def test_missing_support_or_citation_cannot_produce_positive_rank():
    result = _parse_assessments(
        [
            assessment(
                "PETR4",
                status="QUALIFIED_OPPORTUNITY",
                rank=1,
                refs=(),
                support=(),
            )
        ],
        ["PETR4"],
        allowed_source_refs=set(),
    )

    assert result[0].priority_rank == 0
    assert result[0].opportunity_status == "INSUFFICIENT_EVIDENCE"


def test_monitor_cannot_receive_a_positive_rank():
    item = assessment("VALE3", status="MONITOR", rank=1)
    try:
        _parse_assessments([item], ["VALE3"], allowed_source_refs=set())
    except ValueError as exc:
        assert "Only qualified opportunities" in str(exc)
    else:
        raise AssertionError("monitor-only thesis unexpectedly received a rank")
