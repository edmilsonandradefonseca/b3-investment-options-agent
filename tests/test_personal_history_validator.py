import runpy
from urllib.error import URLError
from pathlib import Path


def test_validator_waits_for_service_readiness(monkeypatch):
    module = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/validate_personal_history_real.py'))
    calls = []
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def connect(*args, **kwargs):
        calls.append(args[0])
        if len(calls) == 1:
            raise URLError(ConnectionRefusedError())
        return Response()
    scope = module['wait_ready'].__globals__
    monkeypatch.setitem(scope, 'urlopen', connect)
    monkeypatch.setitem(scope, 'sleep', lambda _: None)
    module['wait_ready']('http://localhost:8000', 5)
    assert calls == ['http://localhost:8000/health'] * 2


def test_validator_accepts_observations_but_rejects_fabricated_results(tmp_path):
    import pytest
    from b3_agent.intelligence.personal_history import PersonalHistoryService
    module = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/validate_personal_history_real.py'))
    body = PersonalHistoryService(tmp_path).build()
    module['validate_observed_projection'](body)
    body['historical_admission']['eligible_outcome_count'] = 1
    with pytest.raises(AssertionError):
        module['validate_observed_projection'](body)
