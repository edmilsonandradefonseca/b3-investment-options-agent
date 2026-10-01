#!/usr/bin/env python3
"""Focused real-runtime read validation; no models or changes to user data."""
import argparse
import json
import os
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import urlopen


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
        print(json.dumps({'ticker':ticker or 'ALL','status':body['status'],'execution_count':body['execution_count'],'sources':body['sources'],'telemetry':body['telemetry']},ensure_ascii=False))
    print('PASS PERSONAL HISTORY READ PROJECTION — lifecycle/learning remain limited')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
