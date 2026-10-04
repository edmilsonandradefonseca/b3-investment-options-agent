"""Scheduled issuer dividend acquisition, projection and optional local analysis."""
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from b3_agent.config import settings
from b3_agent.dividend_evidence import dividend_payload
from b3_agent.knowledge.evidence import Evidence,EvidenceKind,EvidenceMetadata
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.jobs.primary_targets import project_targets


class DividendRefreshJob:
    def __init__(self,provider=None,*,project=project_targets,queue=None,fallback=None):
        if provider is None:
            from b3_agent.providers.brapi.fundamentals import BrapiFundamentalsAdapter
            provider=BrapiFundamentalsAdapter()
            if fallback is None:
                from b3_agent.providers.bradesco_dividends import acquire_monthly_dividends
                fallback=acquire_monthly_dividends
        self.provider=provider;self.project=project;self.fallback=fallback
        self.queue=queue or LocalEvidenceQueue(settings.data_dir/'derived'/'local_evidence_analyst')

    def run(self,tickers):
        tickers=list(dict.fromkeys(tickers))
        if not 1<=len(tickers)<=20: raise ValueError('Refresh requires one to twenty explicit assets')
        from b3_agent.strategy_live import _validated_equity_ticker
        tickers=[_validated_equity_ticker(t) for t in tickers]
        results=[]
        for ticker in tickers:
            start=datetime.now(timezone.utc).date()-timedelta(days=366)
            raw={'status':'UNSUPPORTED_PROVIDER','records':[]}
            getter=getattr(self.provider,'get_dividends',None)
            if getter:
                try:
                    records=[asdict(r) for r in getter(ticker,start=start)]
                    if len(records)>200: raise ValueError('Dividend collection exceeds supported bound')
                    raw={'status':'READ_OK','records':records}
                except (OSError,RuntimeError,ValueError) as exc:
                    raw={'status':'PROVIDER_UNAVAILABLE','records':[],'error_type':type(exc).__name__,'http_status':getattr(exc,'code',None)}
            if raw['status']=='PROVIDER_UNAVAILABLE' and ticker in {'BBDC3','BBDC4'} and self.fallback:
                try:
                    alternative=self.fallback(ticker)
                    if alternative.get('status')!='READ_OK': raise ValueError('Primary fallback unavailable')
                    raw={**alternative,'upstream_error_type':raw.get('error_type'),'upstream_http_status':raw.get('http_status')}
                except (OSError,RuntimeError,ValueError) as exc:
                    raw['fallback_error_type']=type(exc).__name__
            cutoff=datetime.now(timezone.utc)
            normalized=json.loads(json.dumps(raw,default=lambda o:o.isoformat()))
            qualified=dividend_payload(ticker,normalized,cutoff)
            records=[r for r in normalized['records'] if r['source_record_id'] in {e['source_record_id'] for e in qualified['events']}]
            extra={'policy_version':'async-dividends-v1','ticker':ticker,'collection_status':raw['status'],'records':records,
                'error_type':raw.get('error_type'),'http_status':raw.get('http_status'),'requested_start':start.isoformat(),
                **{k:raw[k] for k in ('coverage_status','parser_version','source_content_sha256','upstream_error_type','upstream_http_status','fallback_error_type') if k in raw}}
            fingerprint=sha256(json.dumps(extra,sort_keys=True).encode()).hexdigest()
            doc=f'dividends:{ticker}:{cutoff.isoformat()}:{fingerprint[:12]}'
            content=f'Issuer dividend snapshot {ticker}; qualified event count {len(records)}; collection {raw["status"]}; coverage not exhaustive.'
            evidence=Evidence(evidence_id=doc,kind=EvidenceKind.MARKET_RESEARCH,title=f'Issuer distributions {ticker}',content=content,
                metadata=EvidenceMetadata(document_id=doc,source=raw.get('snapshot_source','https://brapi.dev/api/v2/dividends'),published_at=cutoff,retrieved_at=cutoff,
                    ticker_refs=(ticker,),topic='issuer_dividend_snapshot',source_quality=raw.get('source_quality','provider'),extra=extra))
            try:
                self.project([evidence])
                queue_status='NOT_REQUESTED'
                if records:
                    # Summaries are versioned by economic events, not refresh time.
                    stable=[{k:v for k,v in e.items() if k!='available_timestamp'} for e in qualified['events']]
                    summary=json.dumps(stable,sort_keys=True,default=lambda o:o.isoformat())
                    if len(summary)>12000: summary=json.dumps({'event_count':len(stable),'events_sha256':sha256(summary.encode()).hexdigest()})
                    event={'evidence_type':'issuer_dividends','evidence_id':sha256(summary.encode()).hexdigest(),'headline':f'Observed issuer dividends {ticker}',
                        'summary':summary,'source_name':'BRADESCO_RI' if raw.get('source_quality')=='primary' else 'BRAPI','source_ref':raw.get('snapshot_source','https://brapi.dev/api/v2/dividends'),'published_at':None}
                    queue_status=self.queue.enqueue(ticker,[event]).queue_status
                results.append({'ticker':ticker,'status':'PROJECTED','collection_status':raw['status'],'event_count':len(records),'queue_status':queue_status})
            except Exception as exc:
                results.append({'ticker':ticker,'status':'PROJECTION_UNAVAILABLE','error_type':type(exc).__name__})
        return {'policy_version':'async-dividends-v1','llm_calls':0,'results':results}
