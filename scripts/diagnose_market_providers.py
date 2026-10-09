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
active_curve_ok = False
for path in ('/market-intelligence/yield-curves?curve=PRE', '/market-intelligence/investor-flows'):
    try:
        with urlopen('http://127.0.0.1:8000'+path, timeout=90) as response:
            data = json.load(response)
        if 'yield-curves' in path:
            active_curve_ok = data.get('status') == 'OK' and len(data.get('observations', [])) > 1
        print(json.dumps({'path': path, 'status': data.get('status'), 'as_of':data.get('as_of'), 'observations':len(data.get('observations', []))}))
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
for location in ('/opt/b3-runtime/.env', '/opt/b3-runtime/config/runtime.env', '/opt/b3-runtime/b3.env', '/opt/joao-runtime/joao.env', '/etc/b3-runtime.env'):
    path=Path(location)
    if path.is_file():
        try:
            from dotenv import dotenv_values
            env=dotenv_values(path)
            print(json.dumps({'config':location,'flow_token_present':bool(env.get('DADOSDE_MERCADO_API_TOKEN'))}))
        except PermissionError:
            print(json.dumps({'config':location,'readable':False}))

pid=subprocess.check_output(['systemctl','show','b3-runtime.service','--property=MainPID','--value'],text=True).strip()
try:
    fields=Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
    token_present=any(field.startswith(b'DADOSDE_MERCADO_API_TOKEN=') and bool(field.partition(b'=')[2].strip()) for field in fields)
    print(json.dumps({'active_process_flow_token_present':token_present}))
except PermissionError:
    print(json.dumps({'active_process_environment_readable':False}))

print(json.dumps({'listener':subprocess.check_output(['ss','-ltnp','sport = :8000'],text=True).strip()}))
for item in Path('/proc').iterdir():
    if not item.name.isdecimal():
        continue
    try:
        args=(item/'cmdline').read_bytes().split(b'\0')
        if not any(arg == b'b3_agent.server:app' or arg == b'b3_agent.runtime.service' for arg in args):
            continue
        values={}
        for field in (item/'environ').read_bytes().split(b'\0'):
            key,sep,value=field.partition(b'=')
            if key in (b'PYTHONPATH', b'B3_AGENT_PROJECT_ROOT'):
                values[key.decode()]=value.decode()
        print(json.dumps({'runtime_process':item.name,'executable':args[0].decode(),'cwd':str((item/'cwd').resolve()),'paths':values}))
    except (OSError,PermissionError):
        pass


import shutil
for name in ('sudo','systemctl'):
    path=shutil.which(name)
    print(json.dumps({'command':name,'path':path,'resolved':str(Path(path).resolve()) if path else None}))
print(json.dumps({'service_start':subprocess.check_output(['systemctl','show','b3-runtime.service','--property=ExecMainStartTimestamp','--property=MainPID'],text=True).strip()}))
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=1) as pool:
    try:
        rows=pool.submit(B3YieldCurveAdapter().get_latest, 'PRE').result(timeout=120)
        print(json.dumps({'thread_curve':'PASS','count':len(rows)}))
    except Exception as exc:
        chain=[]
        while exc:
            chain.append({'type':type(exc).__name__, 'message':str(exc)[:300]})
            exc=exc.__cause__
        print(json.dumps({'thread_curve':'FAILED','chain':chain}))
if '--require-curve' in sys.argv:
    assert active_curve_ok, 'ACTIVE_CURVE_HTTP_FAILED: provider correction is not certified on active API'
    print('ACTIVE_CURVE_HTTP=PASS')
