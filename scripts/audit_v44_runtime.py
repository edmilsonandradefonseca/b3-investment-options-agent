"""Read-only runtime evidence. Never print holdings, tokens, or raw responses."""
import json
import subprocess
import time
from urllib.request import urlopen


def command(*args):
    result = subprocess.run(args, text=True, capture_output=True, timeout=15)
    return result.stdout.strip() if result.returncode == 0 else 'UNAVAILABLE'


root = '/opt/b3-investment-options-agent'
print(json.dumps({'checkout_sha': command('git', '-C', root, 'rev-parse', 'HEAD'),
                  'branch': command('git', '-C', root, 'branch', '--show-current'),
                  'tracked_clean': command('git', '-C', root, 'status', '--porcelain', '--untracked-files=no') == '',
                  'service': command('systemctl', 'show', 'b3-runtime.service', '--property=ActiveState,MainPID,ExecMainStartTimestamp')}), flush=True)
for path in ('/health', '/version', '/analysis/live/PETR4'):
    started = time.monotonic()
    try:
        with urlopen('http://127.0.0.1:8000' + path, timeout=45) as response:
            data = json.load(response)
        result = {'path': path, 'ok': True, 'elapsed_s': round(time.monotonic()-started, 2), 'fields': sorted(data)}
        if path == '/health':
            result['llm_enabled'] = data.get('llm_enabled')
        if path == '/version':
            result['version'] = {k: data[k] for k in ('version', 'git_sha', 'commit', 'build_sha') if k in data}
        if path.endswith('PETR4'):
            market = data.get('market', {})
            result.update(history_count=market.get('history_count'), quote_date=market.get('latest', {}).get('observation_timestamp'), options_count=data.get('options', {}).get('contract_count'))
        print(json.dumps(result), flush=True)
    except Exception as exc:
        print(json.dumps({'path': path, 'ok': False, 'error_type': type(exc).__name__}), flush=True)

# LAB-01/02: exact free-text contract used by the central session, no form defaults.
from urllib.request import Request
started = time.monotonic()
try:
    request = Request('http://127.0.0.1:8000/orchestrate', data=json.dumps({
        'task': 'Tenho R$ 10 mil. Comprar ITUB4 ou BBDC4?',
        'ticker': None,
        'context': {'workspace': 'Strategy Lab', 'research_mode': 'stored_first', 'lab_conversation': [], 'lab_request_kind': 'new_analysis'},
    }).encode(), headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=210) as response:
        data = json.load(response)
    result = data.get('result', {})
    synthesis = result.get('synthesis') or {}
    print(json.dumps({'case': 'LAB-01/02-live', 'http_ok': True, 'has_error': bool(data.get('error')),
                      'status': data.get('status'), 'synthesis_status': result.get('derived_synthesis_status'),
                      'result_fields': sorted(result), 'summary_chars': len(str(synthesis.get('summary') or (result.get('proposal') or {}).get('thesis') or result.get('summary') or '')),
                      'comparison_rows': len((result.get('stock_purchase_comparison') or {}).get('rows') or []),
                      'elapsed_s': round(time.monotonic()-started, 2)}), flush=True)
except Exception as exc:
    print(json.dumps({'case': 'LAB-01/02-live', 'http_ok': False, 'error_type': type(exc).__name__, 'elapsed_s': round(time.monotonic()-started, 2)}), flush=True)
