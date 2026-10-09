#!/usr/bin/env python3
"""Focused real-runtime read validation; no models or changes to user data."""
import argparse
import json
import os
from datetime import datetime, timezone
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import urlopen
from urllib.parse import urlencode


def validate_observed_projection(body):
    assert isinstance(body['observed_sequence_count'], int), body
    assert body['observed_sequence_count'] >= len(body['observed_sequences']), body
    assert len(body['observed_sequences']) <= 10, body
    admission = body['historical_admission']
    assert admission['policy_version'] == 'personal-history-admission-v1', admission
    assert admission['eligible_outcome_count'] == 0, admission
    assert admission['similarity_confidence'] is None, admission
    assert admission['ranking_effect'] == 'NONE', admission
    assert admission['unknown_outcome_count'] == body['observed_sequence_count'], admission
    for sequence in body['observed_sequences']:
        assert sequence['opening_balance_assumption'] == 'ZERO_UNVERIFIED', sequence
        assert sequence['economic_outcome_status'] == 'UNKNOWN', sequence
        assert sequence['eligible_for_learning'] is False, sequence
        for key in ('current_position_quantity', 'realized_pnl', 'assigned', 'exercised', 'expired_otm', 'roll_chain_result'):
            assert sequence[key] is None, sequence
        assert len(sequence['movements']) <= 20, sequence
        assert sequence['source_transaction_ids'], sequence
        assert sequence['status'] in {'OBSERVED_NET_FLAT_SEQUENCE', 'OBSERVED_OUTSTANDING_DELTA'}, sequence
        if sequence['status'] == 'OBSERVED_NET_FLAT_SEQUENCE':
            assert sequence['observed_quantity_delta'] == 0, sequence


def wait_ready(base_url, timeout):
    deadline = monotonic() + timeout
    while True:
        try:
            with urlopen(base_url + "/health", timeout=min(3, max(0.1, deadline-monotonic()))) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            pass
        if monotonic() >= deadline:
            raise RuntimeError(f"API unavailable at {base_url}; inspect systemctl status and journalctl for b3-runtime.service")
        sleep(min(1, max(0, deadline-monotonic())))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default=os.getenv('B3_API_URL', 'http://127.0.0.1:8000'))
    parser.add_argument("--ready-timeout", type=float, default=60)
    parser.add_argument('--check-observed-lifecycle', action='store_true', help='Validate bounded execution movements and the strict availability cutoff; no providers/models')
    args=parser.parse_args()
    wait_ready(args.base_url.rstrip("/"), args.ready_timeout)
    for ticker in ('', 'PETR4', 'VALE3', 'RENT3'):
        with urlopen(args.base_url.rstrip('/')+'/history/context'+('?ticker='+ticker if ticker else ''),timeout=20) as response:
            body=json.load(response)
        assert body['status'] in {'LIMITED','NO_MATCHING_EXECUTIONS'}, body
        assert body['coverage']=='UNKNOWN', body
        assert body['assignment_frequency'] is None, body
        assert body['expiry_frequency'] is None, body
        assert body['roll_frequency'] is None, body
        assert body['learning_sample_size']==0, body
        report = {'ticker':ticker or 'ALL','status':body['status'],'execution_count':body['execution_count'],'sources':body['sources'],'telemetry':body['telemetry']}
        if args.check_observed_lifecycle:
            validate_observed_projection(body)
            report.update(observed_sequence_count=body['observed_sequence_count'], admission=body['historical_admission'], observed_sequences=body['observed_sequences'])
            params = {'as_of': datetime.now(timezone.utc).isoformat()}
            if ticker:
                params['ticker'] = ticker
            with urlopen(args.base_url.rstrip('/') + '/history/context?' + urlencode(params), timeout=20) as response:
                strict = json.load(response)
            assert strict['mode'] == 'STRICT_KNOWN_AT_TIME', strict
            validate_observed_projection(strict)
            assert strict['coverage'] == 'UNKNOWN', strict
            report['strict_cutoff'] = {'execution_count': strict['execution_count'], 'excluded': strict['excluded']}
        print(json.dumps(report,ensure_ascii=False))
    print('PASS PERSONAL HISTORY READ PROJECTION — lifecycle/learning remain limited')
    if args.check_observed_lifecycle:
        print('PASS OBSERVED LIFECYCLE + STRICT HISTORY CUTOFF — complete UC-07/08/09 NOT VALIDATED')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
