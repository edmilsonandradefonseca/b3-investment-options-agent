from datetime import date

from b3_agent.repositories.option_contract_registry import (
    OptionContractRecord,
    OptionContractRegistry,
)


def test_contract_metadata_survives_position_closure(tmp_path):
    registry = OptionContractRegistry(tmp_path / "contracts.sqlite3")

    registry.upsert(
        OptionContractRecord(
            option_ticker="EQTLV369",
            expiration_date=date(2026, 10, 16),
            option_type="PUT",
            strike=36.90,
            underlying_ticker="EQTL3",
            contract_multiplier=1,
            source_ref="BTG current positions",
        )
    )

    loaded = registry.get("EQTLV369")

    assert loaded is not None
    assert loaded.expiration_date == date(2026, 10, 16)
    assert loaded.option_type == "PUT"
    assert loaded.strike == 36.90
    assert loaded.underlying_ticker == "EQTL3"


def test_upsert_does_not_erase_existing_metadata_with_partial_record(tmp_path):
    registry = OptionContractRegistry(tmp_path / "contracts.sqlite3")

    registry.upsert(
        OptionContractRecord(
            option_ticker="EQTLV369",
            expiration_date=date(2026, 10, 16),
            strike=36.90,
            underlying_ticker="EQTL3",
            source_ref="source-a",
        )
    )
    registry.upsert(
        OptionContractRecord(
            option_ticker="EQTLV369",
            option_type="PUT",
            source_ref="source-b",
        )
    )

    loaded = registry.get("EQTLV369")

    assert loaded is not None
    assert loaded.expiration_date == date(2026, 10, 16)
    assert loaded.strike == 36.90
    assert loaded.underlying_ticker == "EQTL3"
    assert loaded.option_type == "PUT"
    assert loaded.source_ref == "source-b"
