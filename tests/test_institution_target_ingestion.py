from datetime import datetime,timezone
import pytest
from b3_agent.institution_target_ingestion import xp_report_evidence
URL='https://conteudos.xpi.com.br/acoes/relatorios/fixture/'
NOW=datetime(2026,10,3,tzinfo=timezone.utc)

def page(text='ITUB4 preço-alvo para R$50/ação ao final de 2027.',title='Itaú (ITUB4)',date='2026-08-06T23:18:02+00:00'):
    return f'<meta property="article:modified_time" content="{date}"><h1>{title}</h1><div class="article-content"><p>{text}</p></div><p>BBDC4 preço-alvo para R$999/ação ao final de 2027.</p>'

def test_extracts_only_explicit_single_equity_primary_report_and_dates_version():
    result=xp_report_evidence(URL,page(),NOW)
    assert result.metadata.extra['price_target']['price_brl']==50
    assert result.metadata.extra['price_target']['horizon_date']=='2027-12-31'
    assert result.metadata.published_at.hour==23
    assert result.metadata.extra['source_content_sha256']
    assert '999' not in result.content

@pytest.mark.parametrize('html',[page(text='ITUB4 preço-alvo R$50'),page(title='ITUB4 BBDC4'),page(date='2026-11-01T00:00:00+00:00'),page(date='2026-08-01'),page(text='BBDC4 preço-alvo para R$50/ação ao final de 2027.'),page(text='ITUB4 preço-alvo para R$50/ação ao final de 2027. ITUB4 preço-alvo para R$51/ação ao final de 2027.')])
def test_incomplete_foreign_conflicting_future_and_naive_report_rejected(html):
    with pytest.raises(ValueError): xp_report_evidence(URL,html,NOW)

def test_spoof_and_aggregate_page_rejected():
    for url in ['https://conteudos.xpi.com.br.evil.example/acoes/relatorios/fixture/','https://conteudos.xpi.com.br/acoes/itub4/']:
        with pytest.raises(ValueError): xp_report_evidence(url,page(),NOW)


def test_reviewed_transport_preserves_source_dates_and_rejects_modified_facts():
    import json
    from dataclasses import asdict
    from b3_agent.institution_target_ingestion import reviewed_evidence
    raw=json.loads(json.dumps(asdict(xp_report_evidence(URL,page(),NOW)),default=lambda o:o.isoformat()))
    restored=reviewed_evidence(raw,NOW)
    assert restored.metadata.retrieved_at==NOW
    assert restored.metadata.retention_class.value=="market_evidence"
    assert restored.metadata.decay_profile.value=="fast"
    raw['content']='tampered'
    with pytest.raises(ValueError): reviewed_evidence(raw,NOW)


def test_background_refresh_uses_existing_local_queue_without_calling_model(tmp_path):
    import json
    from dataclasses import asdict
    from urllib.error import HTTPError
    from b3_agent.jobs.primary_targets import PrimaryTargetRefreshJob
    from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
    item=xp_report_evidence(URL,page(),NOW)
    path=tmp_path/'sources.json'
    path.write_text(json.dumps({'schema_version':'reviewed-primary-target-evidence-v1','evidence':[asdict(item)]},default=lambda o:o.isoformat()))
    queue=LocalEvidenceQueue(tmp_path/'queue');projected=[]
    def unavailable(url): raise HTTPError(url,403,'Forbidden',None,None)
    job=PrimaryTargetRefreshJob(acquire=unavailable,project=lambda rows:projected.extend(rows),queue=queue)
    first=job.run(path);second=job.run(path)
    assert first['llm_calls']==0
    assert first['results'][0]['acquisition_status']=='HTTP403_IMPORTED_REVIEWED_PRIMARY_RECORD'
    assert first['results'][0]['queue_status']=='ENQUEUED'
    assert second['results'][0]['queue_status']=='ALREADY_QUEUED'
    assert len(queue.pending())==1 and projected[0].metadata.retrieved_at==NOW
