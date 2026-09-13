import pytest

from b3_agent.providers import DataProvider


def test_data_provider_is_abstract():
    with pytest.raises(TypeError):
        DataProvider()
