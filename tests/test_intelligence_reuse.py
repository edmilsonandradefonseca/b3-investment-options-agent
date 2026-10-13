from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from b3_agent.intelligence.reuse import ContextReuse
from b3_agent.llm.reuse import ReusingLLMClient


def test_singleflight_and_copy_isolation():
    reuse = ContextReuse()
    entered, release = Event(), Event()
    calls=[]
    def build():
        calls.append(1)
        entered.set()
        assert release.wait(3)
        return {'x': []}
    with ThreadPoolExecutor(2) as pool:
        a=pool.submit(reuse.get_or_build,'same',build)
        assert entered.wait(3)
        b=pool.submit(reuse.get_or_build,'same',build)
        release.set()
        first, second = a.result(), b.result()
    first[0]['x'].append('mutated')
    assert second[0] == {'x': []}
    assert len(calls) == 1


def test_failures_not_cached():
    cache=ContextReuse()
    with pytest.raises(ValueError):
        cache.get_or_build('key',lambda: (_ for _ in ()).throw(ValueError('bad')))
    assert cache.get_or_build('key',lambda: 'ok')[0] == 'ok'


def test_llm_exact_input_reuse_invalidation_and_telemetry():
    class Client:
        def __init__(self): self.calls=[]
        def complete_json(self,**kwargs):
            self.calls.append(kwargs)
            return {'answer':'UNKNOWN'}
    raw=Client()
    client=ReusingLLMClient(raw)
    params=dict(instructions='v1',schema_name='x',schema={'required':['answer']},input_text='{"as_of":"t1", "capital":1}')
    client.complete_json(**params)
    client.complete_json(**params)
    assert client.last_telemetry['cache'] == 'HIT'
    assert len(raw.calls)==1
    client.complete_json(**{**params,'input_text':'{"as_of":"t2","capital":1}'})
    client.complete_json(**{**params,'instructions':'v2'})
    assert len(raw.calls)==3
    assert client.last_telemetry['input_chars'] > 0
