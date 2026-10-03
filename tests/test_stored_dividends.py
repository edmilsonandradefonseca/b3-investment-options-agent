from datetime import datetime,timezone,timedelta,date
from dataclasses import asdict
from urllib.error import HTTPError
from types import SimpleNamespace
from b3_agent.stored_dividends import StoredDividendService
from b3_agent.jobs.dividend_refresh import DividendRefreshJob
from b3_agent.schemas.dividend import DividendRecord
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
NOW=datetime(2026,10,3,23,tzinfo=timezone.utc)

def snapshot(**changes):
    m={'document_id':'one','topic':'issuer_dividend_snapshot','ticker_refs':['ITUB4'],'source_quality':'provider','source':'https://brapi.dev/api/v2/dividends','retrieved_at':NOW.timestamp(),
       'extra':{'policy_version':'async-dividends-v1','ticker':'ITUB4','collection_status':'READ_OK','records':[{'ticker':'ITUB4','gross_amount':1}]}}
    m.update(changes);return m

def test_latest_failed_collection_does_not_become_zero_or_resurrect_prior_income():
    bad=snapshot(retrieved_at=(NOW+timedelta(seconds=1)).timestamp(),extra={'policy_version':'async-dividends-v1','ticker':'ITUB4','collection_status':'PROVIDER_UNAVAILABLE','records':[],'http_status':403})
    result=StoredDividendService(lambda t,c:[snapshot(),bad]).build('ITUB4',NOW+timedelta(seconds=2))
    assert result['status']=='PROVIDER_UNAVAILABLE' and result['http_status']==403 and not result['records']
    assert result['read_origin']=='STORED_ASYNC_SNAPSHOT'

def test_future_foreign_stale_conflicting_and_unavailable_snapshots_preserve_unknown():
    for meta in (snapshot(retrieved_at=(NOW+timedelta(seconds=1)).timestamp()),snapshot(ticker_refs=['BBDC4']),snapshot(source='foreign')):
        assert StoredDividendService(lambda t,c:[meta]).build('ITUB4',NOW)['status']=='NO_STORED_SNAPSHOT'
    assert StoredDividendService(lambda t,c:[snapshot()]).build('ITUB4',NOW+timedelta(days=4))['status']=='STALE_STORED_SNAPSHOT'
    two=snapshot(extra={'policy_version':'async-dividends-v1','ticker':'ITUB4','collection_status':'READ_OK','records':[]})
    assert StoredDividendService(lambda t,c:[snapshot(),two]).build('ITUB4',NOW)['status']=='CONFLICTING_SNAPSHOTS'
    def fail(t,c): raise RuntimeError('no store')
    assert StoredDividendService(fail).build('ITUB4',NOW)['status']=='STORE_UNAVAILABLE'

def test_background_job_qualifies_projects_and_deduplicates_local_queue(tmp_path):
    observed=NOW-timedelta(days=5)
    r=DividendRecord(instrument_id='ITUB4',ticker='ITUB4',observation_timestamp=observed,available_timestamp=observed,ingested_at=observed,source='brapi',source_record_id='event1',payment_type='DIVIDEND',gross_amount=1.,announcement_date=date(2026,9,28),payment_date=date(2026,10,2))
    projected=[];queue=LocalEvidenceQueue(tmp_path/'queue')
    job=DividendRefreshJob(SimpleNamespace(get_dividends=lambda ticker,start:[r]),project=lambda rows:projected.extend(rows),queue=queue)
    first=job.run(['ITUB4']);second=job.run(['ITUB4'])
    assert first['results'][0]['event_count']==1 and first['llm_calls']==0
    assert first['results'][0]['queue_status']=='ENQUEUED'
    assert second['results'][0]['queue_status']=='ALREADY_QUEUED'
    metadata=asdict(projected[-1].metadata);result=StoredDividendService(lambda t,c:[metadata]).build('ITUB4',datetime.now(timezone.utc))
    assert result['records'][0]['source_record_id']=='event1'
    assert len(queue.pending())==1

def test_failed_provider_is_projected_as_explicit_failure(tmp_path):
    def fail(ticker,start): raise HTTPError('fixture',403,'Forbidden',None,None)
    projected=[]
    job=DividendRefreshJob(SimpleNamespace(get_dividends=fail),project=lambda rows:projected.extend(rows),queue=LocalEvidenceQueue(tmp_path))
    assert job.run(['BBDC4'])['results'][0]['collection_status']=='PROVIDER_UNAVAILABLE'
    assert projected[0].metadata.extra['http_status']==403
