"""Read-only acceptance of current-position selection and real option management."""
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
for name in ('src/b3_agent/server.py', 'src/b3_agent/routing/lab_position.py',
             'src/b3_agent/routing/lab_option_management.py', 'src/b3_agent/strategy_live.py'):
    installed = runtime/name
    assert hashlib.sha256(installed.read_bytes()).digest() == hashlib.sha256(Path(name).read_bytes()).digest()
    assert started >= installed.stat().st_mtime, 'Restart required after installation'
print('ACTIVE_REVISION_AND_RESTART=PASS', flush=True)
# Runner and systemd environments differ. Read only public path settings and never print credentials.
process_environment = Path(f'/proc/{pid}/environ').read_bytes().split(bytes((0,)))
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
context = {'workspace': 'Strategy Lab', 'analysis_mode': 'deterministic'}
accepted = False
with httpx.Client(base_url='http://127.0.0.1:8000', timeout=15) as client:
    # Verify deterministic option management and output against the installed service revision.
    # Try each open option until one has an admissible later executable quote; keep quote rules strict.
    for position in positions:
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
        selected_turns = [
            {'question': f'Quero encerrar {position.ticker}.', 'response': first['result']},
            {'question': 'Toda a posição.', 'response': payload['result']},
        ]
        compare_context = {**context, 'lab_request_kind': 'follow_up', 'lab_conversation': selected_turns}
        response = client.post('/orchestrate', json={
            'task': 'Compare manter, encerrar e rolar.', 'context': compare_context})
        assert response.status_code == 200
        candidates_response = response.json()
        assert candidates_response['status'] == 'NEEDS_CLARIFICATION'
        assert candidates_response['result']['telemetry'] == {'llm_calls': 0, 'option_chain_calls': 1}
        candidates = candidates_response['result']['lab_roll_candidates']
        if not candidates:
            continue
        candidate = candidates[0]
        selected_turns.append({'question': 'Compare manter, encerrar e rolar.',
                               'response': candidates_response['result']})
        response = client.post('/orchestrate', json={
            'task': candidate['option_id'],
            'context': {**context, 'lab_request_kind': 'follow_up',
                        'lab_conversation': selected_turns}})
        assert response.status_code == 200
        result_response = response.json()
        assert result_response['status'] == 'COMPLETED', (
            f"Chosen roll destination did not complete: status={result_response.get('status')}; "
            f"missing_fields={(result_response.get('result', {}).get('lab_clarification') or {}).get('missing_fields')}"
        )
        result = result_response['result']
        assert result['policy_version'] == 'lab-option-management-v1'
        assert [item['alternative_id'] for item in result['alternatives']] == ['KEEP', 'CLOSE', 'ROLL']
        assert result['position']['option_id'] == position.ticker
        assert result['position']['selected_quantity_units'] == abs(position.quantity)
        assert result['comparison']['ranking'] == 'NOT_APPLIED'
        assert result['derived_synthesis_status'] == 'NOT_REQUESTED'
        assert result['telemetry'] == {'llm_calls': 0, 'option_chain_calls': 1}
        close_leg = result['alternatives'][1]['legs'][0]
        roll_legs = result['alternatives'][2]['legs']
        assert close_leg['contract_id'] == position.ticker
        assert roll_legs[1]['contract_id'] == candidate['option_id']
        assert close_leg['trade_side'] == ('BUY' if position.quantity < 0 else 'SELL')
        all_legs = [close_leg, *roll_legs]
        assert all(leg['price_field'] == ('ask' if leg['trade_side'] == 'BUY' else 'bid')
                   for leg in all_legs)
        assert all(leg['contract_multiplier'] > 0 and leg['source'] and leg['quote_as_of']
                   for leg in all_legs)
        assert all(item['accumulated_realized_pnl_brl'] is None for item in result['alternatives'])
        assert result['portfolio_after_close']['cash_status'] == 'UNKNOWN_COSTS_OR_CASH_BASIS'
        accepted = True
        break
assert accepted, 'No open BTG option has an eligible real OPLAB roll destination; management comparison not accepted'
assert hashlib.sha256(path.read_bytes()).hexdigest() == revision
print('ACTIVE_LAB_CURRENT_POSITION_QUANTITY_ROLL_AND_COMPARISON=PASS', flush=True)
