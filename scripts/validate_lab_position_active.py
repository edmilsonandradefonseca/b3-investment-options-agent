"""Read-only acceptance of position selection; never submits an order."""
import hashlib
import os
from datetime import datetime
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

import httpx

from b3_agent.config import load_settings
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader

runtime = Path('/opt/b3-investment-options-agent')
pid = int(subprocess.check_output(['systemctl', 'show', 'b3-runtime.service', '--property=MainPID', '--value'], text=True, timeout=10))
assert pid > 0
boot = next(int(line.split()[1]) for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))
fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
started = boot + int(fields[19]) / os.sysconf('SC_CLK_TCK')
for name in ('src/b3_agent/server.py', 'src/b3_agent/routing/lab_position.py'):
    installed = runtime/name
    assert hashlib.sha256(installed.read_bytes()).digest() == hashlib.sha256(Path(name).read_bytes()).digest()
    assert started >= installed.stat().st_mtime, 'Restart required after installation'
print('ACTIVE_REVISION_AND_RESTART=PASS', flush=True)
# The runner environment differs from systemd. Read only the two public path
# settings; never load or print provider credentials from the process environment.
process_environment = Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
for name in ('B3_AGENT_PROJECT_ROOT', 'B3_AGENT_DATA_DIR'):
    prefix = name.encode() + b'='
    value = next((field[len(prefix):].decode() for field in process_environment if field.startswith(prefix)), None)
    if value is not None:
        os.environ[name] = value
    else:
        os.environ.pop(name, None)
settings = load_settings()
path = settings.data_dir/'imports'/'portfolio.xlsx'
revision = hashlib.sha256(path.read_bytes()).hexdigest()
portfolio = BtgRendaVariavelLoader().load(path)
today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
positions = [p for p in portfolio.positions if p.instrument_type == 'OPTION' and p.expiration_date >= today]
assert positions, 'No open option in current BTG snapshot; real selection acceptance unavailable'
position = positions[0]
context = {'workspace': 'Strategy Lab'}
with httpx.Client(base_url='http://127.0.0.1:8000', timeout=15) as client:
    response = client.post('/orchestrate', json={'task': f'Quero encerrar {position.ticker}.', 'context': context})
    assert response.status_code == 200
    first = response.json()
    assert first['status'] == 'NEEDS_CLARIFICATION'
    assert first['result']['lab_clarification']['missing_fields'] == ['quantity_units']
    follow = {**context, 'lab_request_kind': 'follow_up', 'lab_conversation': [{'question': f'Quero encerrar {position.ticker}.', 'response': first['result']}]}
    response = client.post('/orchestrate', json={'task': 'Toda a posição.', 'context': follow})
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'INPUTS_IDENTIFIED'
    selection = payload['result']['lab_position_selection']
    assert selection['portfolio_revision'] == revision
    assert selection['selected_quantity_units'] == abs(position.quantity)
    assert selection['position']['quantity'] == position.quantity
    assert selection['operation_calculated'] is False
    assert selection['execution_authorized'] is False
    assert payload['result']['telemetry'] == {'llm_calls': 0, 'option_chain_calls': 0}
assert hashlib.sha256(path.read_bytes()).hexdigest() == revision
print('ACTIVE_LAB_CURRENT_POSITION_AND_QUANTITY=PASS; calculations pending', flush=True)
