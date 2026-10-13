"""Periodic discovery is not factual admission; only source parsers admit targets."""
from urllib.parse import urlparse

from b3_agent.jobs.primary_targets import project_targets, enqueue_target
from b3_agent.institution_target_ingestion import acquire_institution_report
from b3_agent.price_target_evidence import HOSTS
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.config import settings


class InstitutionTargetDiscoveryJob:
    def __init__(self, *, search=None, acquire=acquire_institution_report, project=project_targets, queue=None):
        self.search = search or SearxngNewsAdapter(timeout=8)
        self.acquire = acquire
        self.project = project
        self.queue = queue or LocalEvidenceQueue(settings.data_dir / 'derived' / 'local_evidence_analyst')

    def run(self, tickers):
        if len(tickers) > 20:
            raise ValueError('At most twenty assets per discovery batch')
        rows = []
        seen = set()
        for ticker in dict.fromkeys(tickers):
            try:
                candidates = self.search.search(ticker, query=f'{ticker} preço-alvo relatório (site:xpi.com.br OR site:btgpactual.com OR site:safra.com.br OR site:itau.com.br OR site:itaucorretora.com.br)', limit=5)
            except Exception as exc:
                rows.append({'ticker': ticker, 'status': 'DISCOVERY_UNAVAILABLE', 'error_type': type(exc).__name__})
                continue
            accepted = 0
            for candidate in candidates:
                url = candidate.url or ''
                parsed = urlparse(url)
                institution = next((name for name, domains in HOSTS.items()
                                    if any(parsed.hostname == host or (parsed.hostname or '').endswith('.' + host) for host in domains)), None)
                if not institution or parsed.scheme != 'https' or parsed.username or parsed.password or url in seen:
                    continue
                seen.add(url)
                accepted += 1
                row = {'ticker': ticker, 'institution': institution, 'source_url': url}
                if not ((institution == 'XP' and parsed.hostname == 'conteudos.xpi.com.br' and parsed.path.startswith('/acoes/relatorios/')) or (institution == 'SAFRA' and parsed.hostname == 'oespecialista.safra.com.br' and parsed.path.startswith('/analise/')) or (institution == 'ITAU' and parsed.hostname in {'www.itau.com.br', 'itau.com.br', 'hub-conteudo.cloud.itau.com.br'} and parsed.path.startswith('/investimentos/analises/')) or (institution == 'BTG' and parsed.hostname == 'content.btgpactual.com' and parsed.path.startswith('/research/files/file/pt-BR/') and parsed.path.endswith('.pdf'))):
                    row['status'] = 'CANDIDATE_NOT_ADMITTED_UNSUPPORTED_LAYOUT'
                else:
                    try:
                        evidence = self.acquire(url)
                        if evidence.metadata.ticker_refs != (ticker,):
                            raise ValueError('Discovered report belongs to another equity')
                    except Exception as exc:
                        row.update(status='SOURCE_NOT_ADMITTED', error_type=type(exc).__name__)
                    else:
                        try:
                            self.project([evidence])
                            row.update(status='PROJECTED', queue_status=enqueue_target(self.queue, evidence))
                        except Exception as exc:
                            row.update(status='PROJECTION_FAILED', error_type=type(exc).__name__)
                rows.append(row)
                if accepted >= 3:
                    break
            if not accepted:
                rows.append({'ticker': ticker, 'status': 'NO_PRIMARY_CANDIDATES'})
        return {'policy_version': 'primary-target-discovery-v1', 'llm_calls': 0, 'results': rows,
                'limitations': ['Search snippets never authorize target values or horizons.',
                                'XP, Safra, Itau and BTG explicit report parsers; aggregate pages and other layouts remain unadmitted.',
                                'Source restrictions and unsupported layouts are not bypassed.']}
