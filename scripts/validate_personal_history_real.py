#!/usr/bin/env python3
"""Focused real-runtime read validation; no models or changes to user data."""
import argparse
import json
from urllib.request import urlopen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    args=parser.parse_args()
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
