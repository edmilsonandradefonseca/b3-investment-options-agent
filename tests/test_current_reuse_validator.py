import io
import runpy
from pathlib import Path
from urllib.error import HTTPError


def test_validation_reports_provider_error_without_false_pass(monkeypatch,capsys):
    scripts=Path(__file__).parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    module=runpy.run_path(str(scripts/'validate_current_reuse_real.py'))
    scope=module['main'].__globals__
    monkeypatch.setattr('sys.argv',['validate_current_reuse_real.py'])
    monkeypatch.setitem(scope,'wait_ready',lambda *args:None)
    requested=[]
    def read(base,path,timeout):
        requested.append(path)
        if '/market/' in path:
            raise HTTPError(base+path,503,'unavailable',{},io.BytesIO(b'{"detail":"read timed out"}'))
        return {'options':[],'reuse_telemetry':{'cache':'HIT'}},1
    monkeypatch.setitem(scope,'read',read)
    assert module['main']()==2
    output=capsys.readouterr().out
    assert 'read timed out' in output and 'INCOMPLETE' in output
    assert 'PASS CURRENT' not in output
    assert len(requested)==3
