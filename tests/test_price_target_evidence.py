from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from b3_agent.price_target_evidence import qualify_targets
NOW=datetime(2026,10,3,22,tzinfo=timezone.utc)

def hit(**changes):
    meta={"ticker_refs":["ITUB4"],"topic":"price_target","source_quality":"primary","source":"https://conteudos.xpi.com.br/acoes/itub4/","document_id":"report:1","published_at":NOW-timedelta(days=1),"retrieved_at":NOW,"extra":{"price_target":{"institution":"XP","ticker":"ITUB4","price_brl":40.,"currency":"BRL","horizon_date":"2027-10-03"}}}
    meta.update(changes)
    return SimpleNamespace(metadata=meta)

def test_qualified_primary_target_has_source_horizon_and_no_consensus():
    result=qualify_targets("ITUB4",[hit()],NOW)
    assert result["rows"][0]["price_brl"]==40
    assert result["rows"][0]["document_id"]=="report:1"
    assert result["consensus"] is None and result["expected_return"] is None

def test_host_spoof_future_old_or_sibling_target_is_excluded():
    for changes in ({"source":"https://xpi.com.br.evil.example/report"},{"published_at":NOW+timedelta(seconds=1)},{"published_at":NOW-timedelta(days=181)},{"retrieved_at":NOW+timedelta(seconds=1)},{"ticker_refs":["BBDC4"]},{"extra":{}},{"source_quality":"provider"}):
        assert not qualify_targets("ITUB4",[hit(**changes)],NOW)["rows"]

def test_ambiguous_expired_or_invalid_target_does_not_enter_context():
    for fields in ({"ticker":"BBDC4"},{"price_brl":float("nan")},{"currency":"USD"},{"horizon_date":"2026-09-30"}):
        target=hit().metadata["extra"]["price_target"].copy(); target.update(fields)
        assert not qualify_targets("ITUB4",[hit(extra={"price_target":target})],NOW)["rows"]

def test_duplicate_and_conflicting_report_targets_do_not_form_consensus():
    one=hit();two=hit();two.metadata["extra"]["price_target"]["price_brl"]=45
    assert len(qualify_targets("ITUB4",[one,one],NOW)["rows"])==1
    result=qualify_targets("ITUB4",[one,two],NOW)
    assert not result["rows"] and "CONFLICTING_REPORT_TARGETS" in result["exclusion_reasons"]

def test_empty_store_preserves_unknown_not_zero_target():
    result=qualify_targets("ITUB4",[],NOW)
    assert result["status"]=="UNKNOWN_NO_ADMISSIBLE_TARGETS"
    assert result["expected_return"] is None
