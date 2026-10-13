import json
from copy import deepcopy
from b3_agent.agents.prompt_context import serialize_senior_context


def expand(document):
    def resolve(value):
        if isinstance(value, dict):
            if set(value) == {'$b3_context_ref'}:
                target = document
                for key in value['$b3_context_ref'].split('/')[1:]:
                    key = key.replace('~1','/').replace('~0','~')
                    target = target[int(key)] if isinstance(target,list) else target[key]
                return resolve(target)
            return {key:resolve(item) for key,item in value.items()}
        return [resolve(item) for item in value] if isinstance(value,list) else value
    return resolve(document)


def test_repeated_evidence_is_lossless_and_smaller_without_mutation():
    pack = {'ticker':'ITUB4','unknown':None,'sources':['provider'], 'facts':[{'value':index,'available_at':'2026-10-02'} for index in range(100)]}
    payload = {'workspace':{'asset':pack},'market':{'asset':deepcopy(pack)}}
    before = deepcopy(payload)
    encoded = serialize_senior_context(payload)
    assert expand(json.loads(encoded)) == payload == before
    assert len(encoded) < len(json.dumps(payload))*0.6


def test_distinct_sources_unknowns_and_pointer_escape_remain_exact():
    pack = {'text':'x'*600,'price':None,'source':'A'}
    payload = {'a/b~c':pack,'same':deepcopy(pack),'different':{**pack,'source':'B'},'zero':{**pack,'price':0}}
    assert expand(json.loads(serialize_senior_context(payload))) == payload


def test_reserved_source_key_disables_reference_projection():
    payload = {'source':{'$b3_context_ref':'original source data','text':'x'*600}}
    payload['copy'] = deepcopy(payload['source'])
    assert json.loads(serialize_senior_context(payload)) == payload
