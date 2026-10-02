#!/usr/bin/env python3
"""Read-only current OPLAB acquisition/reuse check; no agents or trading."""
import argparse
import json
import os
from time import monotonic
from urllib.request import urlopen
from urllib.parse import quote
from validate_personal_history_real import wait_ready


def read(base, path):
    started=monotonic()
    with urlopen(base+path,timeout=45) as response:
        body=json.load(response)
    return body, (monotonic()-started)*1000


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default=os.getenv('B3_API_URL','http://127.0.0.1:8000'))
    parser.add_argument('--ticker',default='VALE3')
    args=parser.parse_args()
    base=args.base_url.rstrip('/')
    ticker=quote(args.ticker.upper().strip(),safe='')
    wait_ready(base,60)
    for kind,path in [('stock',f'/market/current/{ticker}'),('chain',f'/options/current/{ticker}?limit=10')]:
        first,first_ms=read(base,path)
        second,second_ms=read(base,path)
        telemetry=second.get('reuse_telemetry',{})
        assert telemetry.get('cache') in {'HIT','COALESCED'}, (kind,telemetry)
        if kind=='stock':
            assert first['quote']==second['quote'], 'Stock acquisition was re-timestamped or changed'
        else:
            assert first['options']==second['options'], 'Option acquisition was re-timestamped or changed'
        print(json.dumps({'kind':kind,'ticker':args.ticker,'first_ms':first_ms,'second_ms':second_ms,'first_reuse':first.get('reuse_telemetry'),'second_reuse':telemetry},ensure_ascii=False))
    print('PASS CURRENT PROVIDER REUSE — no full-agent latency claim')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
