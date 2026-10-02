#!/usr/bin/env python3
"""Read-only current OPLAB acquisition/reuse check; no agents or trading."""
import argparse
import json
import os
from time import monotonic
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from validate_personal_history_real import wait_ready


def read(base, path, timeout=120):
    started=monotonic()
    with urlopen(base+path,timeout=timeout) as response:
        body=json.load(response)
    return body, (monotonic()-started)*1000


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default=os.getenv('B3_API_URL','http://127.0.0.1:8000'))
    parser.add_argument('--ticker',default='VALE3')
    parser.add_argument('--request-timeout',type=float,default=120)
    args=parser.parse_args()
    base=args.base_url.rstrip('/')
    ticker=quote(args.ticker.upper().strip(),safe='')
    wait_ready(base,60)
    failures=[]
    for kind,path in [('stock',f'/market/current/{ticker}'),('chain',f'/options/current/{ticker}?limit=10')]:
        try:
            first,first_ms=read(base,path,args.request_timeout)
            second,second_ms=read(base,path,args.request_timeout)
        except HTTPError as exc:
            try:
                detail=json.loads(exc.read(4096).decode()).get('detail','Provider unavailable')
            except (ValueError, UnicodeError):
                detail='Provider unavailable; non-JSON error body'
            failures.append(kind)
            print(json.dumps({'kind':kind,'status':'UNAVAILABLE','http_status':exc.code,'detail':detail},ensure_ascii=False))
            continue
        except (URLError, TimeoutError, OSError) as exc:
            failures.append(kind)
            print(json.dumps({'kind':kind,'status':'TRANSPORT_ERROR','detail':str(exc)},ensure_ascii=False))
            continue
        telemetry=second.get('reuse_telemetry',{})
        assert telemetry.get('cache') in {'HIT','COALESCED'}, (kind,telemetry)
        if kind=='stock':
            assert first['quote']==second['quote'], 'Stock acquisition was re-timestamped or changed'
        else:
            assert first['options']==second['options'], 'Option acquisition was re-timestamped or changed'
        print(json.dumps({'kind':kind,'ticker':args.ticker,'first_ms':first_ms,'second_ms':second_ms,'first_reuse':first.get('reuse_telemetry'),'second_reuse':telemetry},ensure_ascii=False))
    if failures:
        print('INCOMPLETE CURRENT PROVIDER REUSE — unavailable: '+', '.join(failures))
        return 2
    print('PASS CURRENT PROVIDER REUSE — no full-agent latency claim')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
