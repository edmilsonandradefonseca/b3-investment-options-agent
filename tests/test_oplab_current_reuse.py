import json
from datetime import datetime, timezone
from b3_agent.intelligence.reuse import ContextReuse
from b3_agent.providers.oplab import adapter as stock_module, options as chain_module


class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps(self.payload).encode()


def test_stock_reuse_preserves_timestamps_and_expires(monkeypatch):
    monkeypatch.setenv('OPLAB_API_TOKEN', 'credential-a')
    clock=[0.0]
    monkeypatch.setattr('b3_agent.intelligence.reuse.monotonic', lambda: clock[0])
    monkeypatch.setattr(stock_module, '_CURRENT_QUOTES', ContextReuse(ttl_seconds=5))
    calls=[]
    def opener(*args, **kwargs):
        calls.append(1)
        return Response({'symbol':'VALE3','open':60,'high':61,'low':59,'close':60,'volume':100,'time':1790884800000})
    monkeypatch.setattr(stock_module.urllib.request, 'urlopen', opener)
    first=stock_module.OplabAdapter().get_current_quote('VALE3')
    next_provider=stock_module.OplabAdapter()
    second=next_provider.get_current_quote('vale3')
    assert first == second and len(calls) == 1
    assert next_provider.last_reuse_telemetry['cache'] == 'HIT'
    assert first.ingested_at == second.ingested_at
    clock[0]=6
    next_provider.get_current_quote('VALE3')
    assert len(calls) == 2
    monkeypatch.setenv('OPLAB_API_TOKEN','credential-b')
    next_provider.get_current_quote('VALE3')
    assert len(calls) == 3
    assert 'credential' not in str(next_provider.last_reuse_telemetry)


def test_chain_reuses_put_call_snapshot_without_retimestamping(monkeypatch):
    monkeypatch.setenv('OPLAB_API_TOKEN','chain-test')
    monkeypatch.setattr(chain_module,'_CURRENT_CHAINS',ContextReuse(ttl_seconds=5))
    calls=[]
    payload=[{'symbol':'VALEV600','type':'PUT','strike':60,'due_date':'2026-10-16','bid':1,'ask':1.2}, {'symbol':'VALEJ600','type':'CALL','strike':60,'due_date':'2026-10-16','bid':2,'ask':2.2}]
    def opener(*args,**kwargs):
        calls.append(1)
        return Response(payload)
    monkeypatch.setattr(chain_module.urllib.request,'urlopen',opener)
    first_provider=chain_module.OplabOptionsAdapter()
    contracts, first=first_provider.get_snapshot('VALE3',datetime(2026,10,1,tzinfo=timezone.utc))
    contracts.clear()
    provider=chain_module.OplabOptionsAdapter()
    contracts, second=provider.get_snapshot('VALE3',datetime(2026,10,2,tzinfo=timezone.utc))
    assert len(calls)==1 and len(contracts)==2
    assert second==first
    assert {c.option_type for c in contracts}=={'PUT','CALL'}
    assert all(q.observation_timestamp==q.ingested_at for q in second)
    assert all('provider_timestamp_missing' in q.quality_flags for q in second)
    assert provider.last_reuse_telemetry['cache']=='HIT'


def test_invalid_chain_is_not_cached(monkeypatch):
    import pytest
    monkeypatch.setenv('OPLAB_API_TOKEN','failure-test')
    monkeypatch.setattr(chain_module,'_CURRENT_CHAINS',ContextReuse(ttl_seconds=5))
    calls=[]
    def opener(*args,**kwargs):
        calls.append(1)
        return Response([{'symbol':'INVALID'}] if len(calls)==1 else [])
    monkeypatch.setattr(chain_module.urllib.request,'urlopen',opener)
    provider=chain_module.OplabOptionsAdapter()
    now=datetime.now(timezone.utc)
    with pytest.raises(ValueError): provider.get_snapshot('VALE3',now)
    assert provider.get_snapshot('VALE3',now)==([],[])
    assert len(calls)==2
