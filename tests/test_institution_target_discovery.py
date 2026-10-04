from types import SimpleNamespace
from datetime import datetime, timezone
from urllib.error import HTTPError

from b3_agent.jobs.institution_target_discovery import InstitutionTargetDiscoveryJob
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.institution_target_ingestion import xp_report_evidence
from test_institution_target_ingestion import page, URL


def test_discovery_rejects_search_snippets_spoof_and_unsupported_layouts(tmp_path):
    candidates = [SimpleNamespace(url=URL), SimpleNamespace(url=URL),
                  SimpleNamespace(url='https://conteudos.xpi.com.br.evil.test/acoes/relatorios/fake/'),
                  SimpleNamespace(url='https://www.safra.com.br/relatorio')]
    search = SimpleNamespace(search=lambda *args, **kwargs: candidates)
    acquired = []
    projected = []
    def acquire(url):
        acquired.append(url)
        return xp_report_evidence(url, page(), datetime.now(timezone.utc))
    queue = LocalEvidenceQueue(tmp_path)
    job = InstitutionTargetDiscoveryJob(search=search, acquire=acquire, project=projected.extend, queue=queue)
    result = job.run(['ITUB4'])
    assert acquired == [URL] and len(projected) == len(queue.pending()) == 1
    assert [r['status'] for r in result['results']] == ['PROJECTED', 'CANDIDATE_NOT_ADMITTED_UNSUPPORTED_LAYOUT']
    assert job.run(['ITUB4'])['results'][0]['queue_status'] == 'ALREADY_QUEUED'


def test_source_failure_does_not_redate_or_project_and_next_asset_continues(tmp_path):
    search = SimpleNamespace(search=lambda *args, **kwargs: [SimpleNamespace(url=URL + args[0])])
    def acquire(url):
        raise HTTPError(url, 403, 'Forbidden', None, None)
    projected = []
    result = InstitutionTargetDiscoveryJob(search=search, acquire=acquire, project=projected.extend,
                                          queue=LocalEvidenceQueue(tmp_path)).run(['ITUB4', 'BBDC4'])
    assert len(result['results']) == 2 and all(r['status'] == 'SOURCE_NOT_ADMITTED' for r in result['results'])
    assert not projected


def test_foreign_equity_cannot_be_projected_from_ticker_search(tmp_path):
    search = SimpleNamespace(search=lambda *args, **kwargs: [SimpleNamespace(url=URL)])
    projected = []
    result = InstitutionTargetDiscoveryJob(search=search, acquire=lambda url: xp_report_evidence(url, page(), datetime.now(timezone.utc)),
                                          project=projected.extend, queue=LocalEvidenceQueue(tmp_path)).run(['BBDC4'])
    assert result['results'][0]['status'] == 'SOURCE_NOT_ADMITTED' and not projected


def test_projection_failure_is_distinct_from_provider_coverage_gap(tmp_path):
    search = SimpleNamespace(search=lambda *args, **kwargs: [SimpleNamespace(url=URL)])
    def project(items):
        raise RuntimeError('store unavailable')
    result = InstitutionTargetDiscoveryJob(search=search, acquire=lambda url: xp_report_evidence(url, page(), datetime.now(timezone.utc)),
                                          project=project, queue=LocalEvidenceQueue(tmp_path)).run(['ITUB4'])
    assert result['results'][0]['status'] == 'PROJECTION_FAILED'
