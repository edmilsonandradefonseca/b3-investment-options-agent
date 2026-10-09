"""Read-only provider diagnosis; never print credentials or response bodies."""
import inspect
import json
import sys
from pathlib import Path
sys.path.insert(0, '/opt/b3-investment-options-agent/src')
import pyettj.ettj as ettj
from b3_agent.providers.b3_yield_curve import B3YieldCurveAdapter
from urllib.request import urlopen
from urllib.error import HTTPError
for name in ('_montar_url', '_extrair_txt', '_parsear_txt', '_validar_output'):
    fn = getattr(ettj, name, None)
    print(json.dumps({'helper': name, 'signature': str(inspect.signature(fn)) if fn else 'MISSING'}))
for path in ('/market-intelligence/yield-curves?curve=PRE', '/market-intelligence/investor-flows'):
    try:
        with urlopen('http://127.0.0.1:8000'+path, timeout=90) as response:
            data = json.load(response)
        print(json.dumps({'path': path, 'status': data.get('status'), 'observations':len(data.get('observations', []))}))
    except HTTPError as exc:
        data=json.load(exc)
        print(json.dumps({'path':path,'http':exc.code,'detail':data.get('detail')}))
try:
    rows=B3YieldCurveAdapter().get_latest('PRE')
    print(json.dumps({'direct_curve':'PASS','count':len(rows)}))
except Exception as exc:
    chain=[]
    while exc:
        chain.append({'type':type(exc).__name__,'message':str(exc)[:300]})
        exc=exc.__cause__
    print(json.dumps({'direct_curve':'FAILED','chain':chain}))
for path in (Path('/opt/b3-investment-options-agent/.env'), Path('/opt/b3-investment-options-agent/.env.local')):
    if path.exists():
        from dotenv import dotenv_values
        env=dotenv_values(path)
        print(json.dumps({'config':str(path),'flow_token_present':bool(env.get('DADOSDE_MERCADO_API_TOKEN'))}))
import subprocess
service = subprocess.check_output(['systemctl','show','b3-runtime.service','--property=EnvironmentFiles','--value'],text=True).strip()
print(json.dumps({'service_environment_files':service}))
for location in ('/opt/b3-runtime/.env', '/opt/b3-runtime/config/runtime.env', '/etc/b3-runtime.env'):
    path=Path(location)
    if path.is_file():
        try:
            from dotenv import dotenv_values
            env=dotenv_values(path)
            print(json.dumps({'config':location,'flow_token_present':bool(env.get('DADOSDE_MERCADO_API_TOKEN'))}))
        except PermissionError:
            print(json.dumps({'config':location,'readable':False}))
