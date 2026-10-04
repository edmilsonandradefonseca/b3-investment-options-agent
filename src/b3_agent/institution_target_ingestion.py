"""Bounded primary report acquisition into the existing evidence projection.

No LLM, aggregate ticker-page target or inferred horizon is admitted. The XP
adapter supports only explicit amount/end-year language in a single-stock report.
Other institutional reports require their own verified adapter.
"""
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import re
import json
from types import SimpleNamespace
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
from b3_agent.price_target_evidence import qualify_targets


class ReportHTML(HTMLParser):
    def __init__(self, body_class='article-content'):
        super().__init__(convert_charrefs=True)
        self.body_class = body_class
        self.depth = 0
        self.article_depth = None
        self.text = []
        self.modified = []
        self.title = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('property') == 'article:modified_time':
            self.modified.append(attrs.get('content'))
        if tag == 'h1': self.in_title = True
        if tag == 'div':
            self.depth += 1
            if self.body_class in attrs.get('class', '').split():
                self.article_depth = self.depth
        if self.article_depth is not None and tag in {'p', 'br'}:
            self.text.append('\n')

    def handle_endtag(self, tag):
        if tag == 'h1': self.in_title = False
        if tag == 'div':
            if self.depth == self.article_depth: self.article_depth = None
            self.depth -= 1

    def handle_data(self, data):
        if self.article_depth is not None: self.text.append(data)
        if self.in_title: self.title.append(data)


def xp_report_evidence(url, html, retrieved_at):
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'conteudos.xpi.com.br'
            or not parsed.path.startswith('/acoes/relatorios/') or parsed.username or parsed.password):
        raise ValueError('Only primary XP single-report URLs are supported')
    page = ReportHTML(); page.feed(html)
    title = ' '.join(page.title)
    tickers = set(re.findall(r'\b[A-Z]{4}\d{1,2}\b', title))
    if len(tickers) != 1 or len(set(page.modified)) != 1:
        raise ValueError('Ambiguous report identity or explicit publication timestamp')
    ticker = tickers.pop()
    published = datetime.fromisoformat(page.modified[0].replace('Z', '+00:00'))
    # An explicit modified timestamp conservatively dates this report version.
    paragraphs = [' '.join(p.split()) for p in ''.join(page.text).split('\n') if p.strip()]
    pattern = r'preço[- ]alvo\s+(?:para|de|em)\s+R\$\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:(?:/|por\s+)\s*ação)?\s*(?:ao|para\s+o|no)\s+final\s+(?:do\s+ano\s+)?de\s+(20\d{2})'
    found = [(m.group(1), m.group(2)) for p in paragraphs if ticker in p for m in re.finditer(pattern, p, re.I)]
    pairs = {(float(amount.replace(',', '.')), year+'-12-31') for amount, year in found}
    if len(pairs) != 1:
        raise ValueError('Missing or conflicting explicit ticker/amount/horizon in report paragraph')
    price, horizon = pairs.pop()
    digest = sha256(html.encode()).hexdigest()
    doc = 'XP:'+sha256((url+published.isoformat()).encode()).hexdigest()
    target = {'institution':'XP', 'ticker':ticker, 'price_brl':price, 'currency':'BRL', 'horizon_date':horizon}
    metadata = EvidenceMetadata(document_id=doc, source=url, published_at=published,
        retrieved_at=retrieved_at, ticker_refs=(ticker,), topic='price_target', source_quality='primary',
        extra={'price_target':target, 'parser_version':'xp-explicit-report-v1',
               'source_content_sha256':digest, 'published_at_semantics':'EXPLICIT_REPORT_VERSION_MODIFIED_AT'})
    if not qualify_targets(ticker, [SimpleNamespace(metadata=asdict(metadata))], retrieved_at)['rows']:
        raise ValueError('Report fails temporal/provenance qualification')
    content = f"Institution XP; equity {ticker}; target BRL {price}; end-year horizon {horizon}; report version {published.isoformat()}."
    return Evidence(evidence_id=doc, kind=EvidenceKind.MARKET_RESEARCH,
        title=f'XP institutional target {ticker}', content=content, metadata=metadata,
        source_url=url, content_hash=sha256(content.encode()).hexdigest())


def acquire_xp_report(url, *, opener=urlopen):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'conteudos.xpi.com.br' or not parsed.path.startswith('/acoes/relatorios/') or parsed.username or parsed.password:
        raise ValueError('Unsupported primary report URL')
    with opener(Request(url, headers={'User-Agent':'B3-Evidence/1.0'}), timeout=15) as response:
        if response.geturl() != url:
            raise ValueError('Report redirect requires independent review')
        data = response.read(2_000_001)
        if len(data) > 2_000_000: raise ValueError('Report too large')
    return xp_report_evidence(url, data.decode('utf-8'), datetime.now(timezone.utc))


def safra_report_evidence(url, html, retrieved_at):
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'oespecialista.safra.com.br'
            or not parsed.path.startswith('/analise/') or parsed.username or parsed.password):
        raise ValueError('Unsupported Safra report URL')
    page = ReportHTML(body_class='page-content'); page.feed(html)
    body = ' '.join(''.join(page.text).split())
    tickers = set(re.findall(r'\b[A-Z]{4}\d{1,2}\b', body))
    if len(tickers) != 1 or len(set(page.modified)) != 1:
        raise ValueError('Ambiguous Safra report identity or version timestamp')
    ticker = tickers.pop()
    published = datetime.fromisoformat(page.modified[0].replace('Z', '+00:00'))
    amount = r'([0-9]+(?:[.,][0-9]{1,2})?)'
    patterns = [
        r'preço[- ]alvo\s+para\s+o\s+final\s+de\s+(20\d{2})\s+é\s+de\s+R\$\s*' + amount,
        r'preço[- ]alvo\s+de\s+R\$\s*' + amount + r'\s+por\s+ação\s+no\s+final\s+de\s+(20\d{2})',
    ]
    pairs = set()
    for index, pattern in enumerate(patterns):
        for match in re.finditer(pattern, body, re.I):
            year, price = match.groups() if index == 0 else reversed(match.groups())
            pairs.add((float(price.replace(',', '.')), year + '-12-31'))
    if len(pairs) != 1:
        raise ValueError('Missing or conflicting explicit Safra target/horizon')
    price, horizon = pairs.pop()
    doc = 'SAFRA:' + sha256((url + published.isoformat()).encode()).hexdigest()
    target = {'institution':'SAFRA', 'ticker':ticker, 'price_brl':price, 'currency':'BRL', 'horizon_date':horizon}
    metadata = EvidenceMetadata(document_id=doc, source=url, published_at=published,
        retrieved_at=retrieved_at, ticker_refs=(ticker,), topic='price_target', source_quality='primary',
        extra={'price_target':target, 'parser_version':'safra-explicit-report-v1',
               'source_content_sha256':sha256(html.encode()).hexdigest(),
               'published_at_semantics':'EXPLICIT_REPORT_VERSION_MODIFIED_AT'})
    if not qualify_targets(ticker, [SimpleNamespace(metadata=asdict(metadata))], retrieved_at)['rows']:
        raise ValueError('Safra report fails temporal/provenance qualification')
    content = f'Institution SAFRA; equity {ticker}; target BRL {price}; horizon {horizon}; report version {published.isoformat()}.'
    return Evidence(evidence_id=doc, kind=EvidenceKind.MARKET_RESEARCH,
        title=f'Safra institutional target {ticker}', content=content, metadata=metadata,
        source_url=url, content_hash=sha256(content.encode()).hexdigest())


def acquire_institution_report(url, *, opener=urlopen):
    if urlparse(url).hostname == 'conteudos.xpi.com.br':
        return acquire_xp_report(url, opener=opener)
    parsed = urlparse(url)
    supported = (parsed.hostname == 'oespecialista.safra.com.br' and parsed.path.startswith('/analise/')) or (parsed.hostname in {'www.itau.com.br', 'itau.com.br', 'hub-conteudo.cloud.itau.com.br'} and parsed.path.startswith('/investimentos/analises/'))
    if parsed.scheme != 'https' or not supported or parsed.username or parsed.password:
        raise ValueError('Unsupported institutional report URL')
    with opener(Request(url, headers={'User-Agent':'B3-Evidence/1.0'}), timeout=15) as response:
        if response.geturl() != url:
            raise ValueError('Report redirect requires independent review')
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError('Report too large')
    parser = safra_report_evidence if parsed.hostname == 'oespecialista.safra.com.br' else itau_report_evidence
    return parser(url, data.decode('utf-8'), datetime.now(timezone.utc))


def reviewed_evidence(raw, cutoff):
    """Import previously acquired, parser-reviewed facts without redating them."""
    m=dict(raw['metadata'])
    for field in ('published_at','retrieved_at','valid_from','valid_to'):
        if m.get(field) is not None: m[field]=datetime.fromisoformat(m[field].replace('Z','+00:00'))
    from b3_agent.knowledge.lifecycle import RetentionClass,DecayProfile
    if 'retention_class' in m: m['retention_class']=RetentionClass(m['retention_class'])
    if 'decay_profile' in m: m['decay_profile']=DecayProfile(m['decay_profile'])
    metadata=EvidenceMetadata(**m)
    target=metadata.extra.get('price_target',{})
    if metadata.extra.get('parser_version') not in {'xp-explicit-report-v1', 'safra-explicit-report-v1', 'itau-explicit-report-v1'} or not re.fullmatch(r'[0-9a-f]{64}',metadata.extra.get('source_content_sha256','')):
        raise ValueError('Missing reviewed parser acquisition provenance')
    if not qualify_targets(target.get('ticker'),[SimpleNamespace(metadata=asdict(metadata))],cutoff)['rows']:
        raise ValueError('Reviewed evidence fails current qualification')
    content=raw['content']
    if sha256(content.encode()).hexdigest()!=raw.get('content_hash') or raw.get('source_url')!=metadata.source:
        raise ValueError('Reviewed content identity mismatch')
    return Evidence(evidence_id=raw['evidence_id'],kind=EvidenceKind(raw['kind']),title=raw['title'],
        content=content,metadata=metadata,source_url=raw['source_url'],content_hash=raw['content_hash'])


class InstitutionalScriptHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None
        self.script_type = None
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.current = []
            self.script_type = dict(attrs).get('type')
    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            self.scripts.append((self.script_type, ''.join(self.current)))
            self.current = None


def itau_report_evidence(url, html, retrieved_at):
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname not in {'www.itau.com.br', 'itau.com.br', 'hub-conteudo.cloud.itau.com.br'}
            or not parsed.path.startswith('/investimentos/analises/') or parsed.username or parsed.password):
        raise ValueError('Unsupported Itau report URL')
    page = InstitutionalScriptHTML(); page.feed(html)
    articles, bodies = [], []
    for script_type, script in page.scripts:
        if script_type == 'application/ld+json':
            payload = json.loads(script)
            nodes = payload.get('@graph', [payload]) if isinstance(payload, dict) else []
            articles.extend(node for node in nodes if node.get('@type') in ('Article', 'NewsArticle'))
        elif script.startswith('self.__next_f.push(') and script.endswith(')'):
            payload = json.loads(script[len('self.__next_f.push('):-1])
            if isinstance(payload, list) and len(payload) == 2 and isinstance(payload[1], str) and payload[1].startswith('<p>'):
                body_page = ReportHTML()
                body_page.feed('<div class="article-content">' + payload[1] + '</div>')
                bodies.append(' '.join(''.join(body_page.text).split()))
    if len(articles) != 1:
        raise ValueError('Ambiguous Itau primary article metadata')
    article = articles[0]
    refs = {str(item.get('@id', '')).rsplit('#corp-', 1)[-1] for item in article.get('mentions', [])}
    if len(refs) != 1 or not re.fullmatch(r'[A-Z]{4}\d{1,2}', next(iter(refs))):
        raise ValueError('Missing exact Itau equity identity')
    ticker = refs.pop()
    bodies = [body for body in bodies if ticker in body and 'preço-alvo' in body.lower()]
    if len(bodies) != 1 or set(re.findall(r'\b[A-Z]{4}\d{1,2}\b', bodies[0])) != {ticker}:
        raise ValueError('Ambiguous Itau report body')
    found = {(float(m.group(1).replace(',', '.')), m.group(2) + '-12-31') for m in re.finditer(
        r'preço[- ]alvo\s+para\s+R\$\s*([0-9]+(?:[.,][0-9]{1,2})?)\s+ao\s+fim\s+de\s+(20\d{2})', bodies[0], re.I)}
    if len(found) != 1:
        raise ValueError('Missing or conflicting explicit Itau target and horizon')
    price, horizon = found.pop()
    published = datetime.fromisoformat(article['dateModified'].replace('Z', '+00:00'))
    doc = 'ITAU:' + sha256((url + published.isoformat()).encode()).hexdigest()
    target = {'institution':'ITAU', 'ticker':ticker, 'price_brl':price, 'currency':'BRL', 'horizon_date':horizon}
    metadata = EvidenceMetadata(document_id=doc, source=url, published_at=published,
        retrieved_at=retrieved_at, ticker_refs=(ticker,), topic='price_target', source_quality='primary',
        extra={'price_target':target, 'parser_version':'itau-explicit-report-v1',
               'source_content_sha256':sha256(html.encode()).hexdigest(),
               'published_at_semantics':'EXPLICIT_REPORT_VERSION_MODIFIED_AT'})
    if not qualify_targets(ticker, [SimpleNamespace(metadata=asdict(metadata))], retrieved_at)['rows']:
        raise ValueError('Itau report fails temporal/provenance qualification')
    content = f'Institution ITAU; equity {ticker}; target BRL {price}; horizon {horizon}; report version {published.isoformat()}.'
    return Evidence(evidence_id=doc, kind=EvidenceKind.MARKET_RESEARCH,
        title=f'Itau institutional target {ticker}', content=content, metadata=metadata,
        source_url=url, content_hash=sha256(content.encode()).hexdigest())
