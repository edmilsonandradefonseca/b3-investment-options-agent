from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.error import HTTPError
from dataclasses import asdict
import pytest
from b3_agent.providers.bradesco_dividends import monthly_records, DOCUMENT_PREFIX, PAGE
from b3_agent.jobs.dividend_refresh import DividendRefreshJob
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.stored_dividends import StoredDividendService
from b3_agent.dividend_evidence import dividend_payload

NOW = datetime(2026,10,4,tzinfo=timezone.utc)
SOURCE = DOCUMENT_PREFIX + 'fixture_aviso_aos_acionistas.pdf'

def notice():
    amounts = 'Banco Bradesco S.A. R$0,017249826 por ação ordinária e R$0,018974809 por ação preferencial, que, líquidos Data de Declaração '
    months = 'Janeiro Fevereiro Março Abril Maio Junho Julho Agosto Setembro Outubro Novembro Dezembro'.split()
    return amounts + ' '.join(f'{month} 1.{i}.2026 2.{i}.2026 3.{i}.2026' for i,month in enumerate(months,1))

def test_monthly_notice_preserves_class_and_future_declaration_unknown():
    pn=monthly_records(notice(),ticker='BBDC4',source=SOURCE,observed_at=NOW)
    on=monthly_records(notice(),ticker='BBDC3',source=SOURCE,observed_at=NOW)
    assert pn[0]['gross_amount']==0.018974809
    assert on[0]['gross_amount']==0.017249826
    assert pn[-1]['announcement_date'] is None
    assert pn[-1]['record_date'].month==12
    payload=dividend_payload('BBDC4',{'status':'READ_OK','records':pn},NOW)
    assert payload['announced_conditional_gross_per_share_brl'] is None
    assert payload['events'][-1]['payment_status']=='FUTURE_PAYMENT_UNVERIFIED_ANNOUNCEMENT'
    for text in [notice().replace('preferencial, que, líquidos','preferencial'),notice().replace('Dezembro','Novembro')]:
        with pytest.raises(ValueError):monthly_records(text,ticker='BBDC4',source=SOURCE,observed_at=NOW)

def test_failed_provider_uses_qualified_primary_snapshot_and_preserves_partial_coverage(tmp_path):
    def failed(ticker,start):raise HTTPError('fixture',403,'Forbidden',None,None)
    def fallback(ticker):
        return {'status':'READ_OK','records':monthly_records(notice(),ticker=ticker,source=SOURCE,observed_at=NOW),
            'snapshot_source':PAGE,'source_quality':'primary','parser_version':'bradesco-monthly-jcp-v1',
            'coverage_status':'PARTIAL_MONTHLY_JCP_ONLY','source_content_sha256':'a'*64}
    projected=[]
    job=DividendRefreshJob(SimpleNamespace(get_dividends=failed),fallback=fallback,project=lambda rows:projected.extend(rows),queue=LocalEvidenceQueue(tmp_path))
    result=job.run(['BBDC4'])
    assert result['results'][0]['event_count']==12
    metadata=asdict(projected[0].metadata)
    read=StoredDividendService(lambda t,c:[metadata]).build('BBDC4',datetime.now(timezone.utc))
    assert read['status']=='READ_OK' and read['coverage_status']=='PARTIAL_MONTHLY_JCP_ONLY'
    assert metadata['extra']['upstream_http_status']==403
    assert metadata['source']==PAGE
    metadata['extra']['parser_version']='unreviewed'
    assert StoredDividendService(lambda t,c:[metadata]).build('BBDC4',datetime.now(timezone.utc))['status']=='NO_STORED_SNAPSHOT'
