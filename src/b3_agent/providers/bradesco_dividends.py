"""Primary monthly JCP schedule; never claims complete issuer distributions."""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
import re
from urllib.request import Request, urlopen

PAGE = 'https://www.bradescori.com.br/informacoes-ao-mercado/remuneracao-aos-acionistas/'
DOCUMENT_PREFIX = 'https://filemanager-cdn.mziq.com/published/80f2e993-0a30-421a-9470-a4d5c8ad5e9f/'


class MonthlyNoticeLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get('href', '')
        if tag == 'a' and href.startswith(DOCUMENT_PREFIX) and href.endswith('_aviso_aos_acionistas.pdf'):
            self.links.add(href)


def _read(url, opener):
    with opener(Request(url, headers={'User-Agent':'B3-Evidence/1.0'}), timeout=15) as response:
        if response.geturl() != url:
            raise ValueError('Unreviewed issuer source redirect')
        value = response.read(2_000_001)
        if len(value) > 2_000_000:
            raise ValueError('Issuer source exceeds acquisition bound')
        return value


def monthly_records(text, *, ticker, source, observed_at):
    if ticker not in {'BBDC3', 'BBDC4'} or not source.startswith(DOCUMENT_PREFIX):
        raise ValueError('Unsupported issuer identity')
    normalized = ' '.join(text.split())
    amount = re.search(r'R\$\s*([0-9]+,[0-9]+)\s+por\s+ação\s+ordinária\s+e\s+R\$\s*([0-9]+,[0-9]+)\s+por\s+ação\s+preferencial,\s+que,\s+líquidos', normalized)
    if not amount or 'Banco Bradesco S.A.' not in normalized or 'Data de Declaração' not in normalized:
        raise ValueError('Unverified gross amount or declaration schedule')
    value = float(amount.group(1 if ticker == 'BBDC3' else 2).replace(',', '.'))
    # Ordinal first-day markers from PDF extraction carry no economic meaning.
    normalized = re.sub(r'1o\s*\.\s*', '1.', normalized)
    months = 'Janeiro Fevereiro Março Abril Maio Junho Julho Agosto Setembro Outubro Novembro Dezembro'.split()
    rows = re.findall(r'(' + '|'.join(months) + r')\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}\.\d{1,2}\.\d{4})', normalized)
    if len(rows) != 12 or {row[0] for row in rows} != set(months):
        raise ValueError('Incomplete or ambiguous monthly declaration schedule')
    records = []
    today = observed_at.date()
    for month, record, ex_date, payment in rows:
        dates = [datetime.strptime(v, '%d.%m.%Y').date() for v in (record, ex_date, payment)]
        if not dates[0] < dates[1] <= dates[2]:
            raise ValueError('Inconsistent issuer schedule dates')
        declared = dates[0] <= today
        records.append({'ticker':ticker, 'instrument_id':ticker, 'source':source,
            'source_record_id': f'{ticker}:monthly-jcp:{dates[0].isoformat()}',
            'observation_timestamp':observed_at, 'available_timestamp':observed_at,
            'ingested_at':observed_at, 'payment_type':'JCP_MONTHLY', 'gross_amount':value,
            'currency':'BRL', 'announcement_date':dates[0] if declared else None,
            'record_date':dates[0], 'ex_date':dates[1], 'payment_date':dates[2],
            'quality_status':'WARNING', 'quality_flags':['PARTIAL_MONTHLY_JCP_ONLY',
                'DECLARATION_DATE_FROM_ISSUER_SCHEDULE' if declared else 'SCHEDULED_NOT_YET_DECLARED']})
    return records


def acquire_monthly_dividends(ticker, *, opener=urlopen):
    from pypdf import PdfReader
    page = _read(PAGE, opener).decode('utf-8')
    links = MonthlyNoticeLinks(); links.feed(page)
    if len(links.links) != 1:
        raise ValueError('No unique issuer-linked monthly notice')
    source = links.links.pop()
    document = _read(source, opener)
    reader = PdfReader(BytesIO(document))
    if len(reader.pages) > 3:
        raise ValueError('Unexpected issuer notice layout')
    text = '\n'.join(p.extract_text() or '' for p in reader.pages)
    now = datetime.now(timezone.utc)
    return {'status':'READ_OK', 'records':monthly_records(text,ticker=ticker,source=source,observed_at=now),
        'snapshot_source':PAGE, 'source_quality':'primary', 'parser_version':'bradesco-monthly-jcp-v1',
        'source_content_sha256':sha256(document).hexdigest(), 'coverage_status':'PARTIAL_MONTHLY_JCP_ONLY'}
