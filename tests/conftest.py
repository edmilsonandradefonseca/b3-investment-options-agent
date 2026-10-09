"""Provider unit tests use isolated local budgets; never write runtime quota."""
import pytest


@pytest.fixture(autouse=True)
def isolated_brapi_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("B3_BRAPI_BUDGET_PATH", str(tmp_path / "brapi.sqlite3"))
    monkeypatch.setenv("B3_BRAPI_LOCAL_ALLOWANCE", "100")
    monkeypatch.setenv("B3_BRAPI_OPERATIONAL_RESERVE", "0")
