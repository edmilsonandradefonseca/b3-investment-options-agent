"""Validate approved natural Lab input on candidate ASGI, not the systemd process."""
import json
import os
from pathlib import Path
import subprocess
from time import monotonic

pid = subprocess.check_output(['systemctl','show','b3-runtime.service','--property=MainPID','--value'],text=True,timeout=10).strip()
assert pid.isdecimal() and int(pid)>0
# Existing runtime validation convention: reuse only B3/provider configuration;
# do not print credentials or raw personal payloads.
for field in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
    key,sep,value=field.partition(b'=')
    name=key.decode('utf-8')
    if sep and (name.startswith('B3_') or name in {'OPLAB_API_TOKEN','BRAPI_TOKEN'}):
        os.environ[name]=value.decode('utf-8')
os.environ['B3_AGENT_DATA_DIR']='/opt/b3-runtime/data'
os.environ['B3_AGENT_PROJECT_ROOT']=str(Path(__file__).resolve().parents[1])
from fastapi.testclient import TestClient
from b3_agent.server import app
client=TestClient(app)
request={'task':'Tenho R$ 10 mil. Comprar ITUB4 ou BBDC4?','ticker':None,'context':{'workspace':'Strategy Lab','research_mode':'stored_only','analysis_mode':'deterministic'}}
started=monotonic()
response=client.post('/orchestrate',json=request)
assert response.status_code==200
result=response.json()
assert not result.get('error')
rows=result['result']['stock_purchase_comparison']['rows']
assert {r['ticker'] for r in rows}=={'ITUB4','BBDC4'}
print(json.dumps({'instance':'candidate ASGI; not active systemd','case':'LAB-01 natural budget','status':'PASS','rows':len(rows),'elapsed_s':round(monotonic()-started,2)}),flush=True)
request['context'].pop('analysis_mode')
request['context']['research_mode']='stored_first'
started=monotonic()
response=client.post('/orchestrate',json=request)
assert response.status_code==200
payload=response.json(); result=payload['result']
assert not payload.get('error')
proposal=result.get('proposal') or result.get('decision_proposal') or {}
assert proposal.get('thesis') and proposal.get('rationale'), 'Missing central senior narrative'
assert len(result['stock_purchase_comparison']['rows'])==2
print(json.dumps({'instance':'candidate ASGI; not active systemd','case':'LAB-02 senior plus canonical comparison','status':'PASS','thesis_chars':len(proposal['thesis']),'rationale_chars':len(proposal['rationale']),'elapsed_s':round(monotonic()-started,2)}),flush=True)
