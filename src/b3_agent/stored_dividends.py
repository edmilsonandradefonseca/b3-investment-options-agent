"""Read qualified dividend collection snapshots from existing Qdrant, no provider."""
from datetime import timedelta
import os
from b3_agent.intelligence.stored_research import _timestamp


def read_snapshots(ticker,cutoff):
    from qdrant_client import QdrantClient,models
    client=QdrantClient(url=os.getenv('B3_QDRANT_URL','http://127.0.0.1:6333'),timeout=3)
    try:
        query=models.Filter(must=[models.FieldCondition(key='ticker_refs',match=models.MatchValue(value=ticker)),
            models.FieldCondition(key='topic',match=models.MatchValue(value='issuer_dividend_snapshot')),
            models.FieldCondition(key='retrieved_at',range=models.Range(lte=cutoff.timestamp(),gte=(cutoff-timedelta(days=7)).timestamp()))])
        result=[];offset=None
        for _ in range(10):
            rows,offset=client.scroll(collection_name='b3_evidence_768_hybrid',scroll_filter=query,limit=100,offset=offset,with_payload=True,with_vectors=False)
            result.extend(dict(row.payload or {}) for row in rows)
            if offset is None: return result
        raise RuntimeError('Dividend snapshot read bound exceeded; latest snapshot is not proven')
    finally: client.close()


class StoredDividendService:
    def __init__(self,reader=read_snapshots): self.reader=reader
    def build(self,ticker,cutoff):
        try: candidates=self.reader(ticker,cutoff)
        except Exception as exc: return {'status':'STORE_UNAVAILABLE','records':[],'error_type':type(exc).__name__}
        admitted=[]
        for meta in candidates:
            available=_timestamp(meta.get('retrieved_at'))
            extra=meta.get('extra') or {}
            if (meta.get('topic')!='issuer_dividend_snapshot' or ticker not in meta.get('ticker_refs',[]) or meta.get('source_quality')!='provider'
                    or meta.get('source')!='https://brapi.dev/api/v2/dividends' or not available or available>cutoff
                    or not meta.get('document_id') or not isinstance(extra,dict) or extra.get('ticker')!=ticker or extra.get('policy_version')!='async-dividends-v1'
                    or extra.get('collection_status') not in {'READ_OK','PROVIDER_UNAVAILABLE','UNSUPPORTED_PROVIDER'}
                    or not isinstance(extra.get('records'),list) or len(extra['records'])>200): continue
            admitted.append((available,meta['document_id'],extra))
        if not admitted: return {'status':'NO_STORED_SNAPSHOT','records':[]}
        latest=max(a[0] for a in admitted); winners=[a for a in admitted if a[0]==latest]
        if len({str(a[2]) for a in winners})>1: return {'status':'CONFLICTING_SNAPSHOTS','records':[]}
        available,doc,extra=winners[0]
        if cutoff-available>timedelta(hours=72): return {'status':'STALE_STORED_SNAPSHOT','records':[],'snapshot_available_at':available}
        return {'status':extra['collection_status'],'records':extra['records'],'error_type':extra.get('error_type'),
            'http_status':extra.get('http_status'),'read_origin':'STORED_ASYNC_SNAPSHOT','snapshot_available_at':available,'snapshot_document_id':doc}
