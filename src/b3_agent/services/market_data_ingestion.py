from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import uuid4

from b3_agent.repositories.data_source import DataSourceRepository
from b3_agent.repositories.dataset_reference import DatasetReferenceRepository
from b3_agent.repositories.ingestion_run import IngestionRunRepository
from b3_agent.repositories.market_data import MarketDataRepository


@dataclass(frozen=True)
class MarketDataIngestionResult:
    run_id: str
    records_read: int
    records_written: int
    records_rejected: int
    storage_path: str


class MarketDataIngestionService:
    def __init__(
        self,
        provider,
        market_data_repository: MarketDataRepository,
        data_source_repository: DataSourceRepository,
        ingestion_run_repository: IngestionRunRepository,
        dataset_reference_repository: DatasetReferenceRepository,
    ):
        self.provider = provider
        self.market_data_repository = market_data_repository
        self.data_source_repository = data_source_repository
        self.ingestion_run_repository = ingestion_run_repository
        self.dataset_reference_repository = dataset_reference_repository

    def ingest(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> MarketDataIngestionResult:
        ticker = ticker.upper().strip()

        if not ticker:
            raise ValueError("ticker must not be empty")

        if start > end:
            raise ValueError("start date must be on or before end date")

        now = datetime.now(timezone.utc)
        run_id = str(uuid4())
        source_id = self.provider.name

        self.data_source_repository.upsert(
            source_id=source_id,
            name=source_id,
            provider_type="market_data",
        )

        self.ingestion_run_repository.create(
            run_id=run_id,
            source_id=source_id,
            dataset="market_data",
            started_at=now.isoformat(),
        )

        try:
            records = self.provider.get_market_data(
                ticker=ticker,
                start=start,
                end=end,
            )

            records_read = len(records)

            if not records:
                raise ValueError(
                    f"provider returned no market data for ticker {ticker}"
                )

            storage_path = self.market_data_repository.write(records)

            first_observation = min(
                record.observation_timestamp for record in records
            )
            last_observation = max(
                record.observation_timestamp for record in records
            )

            self.dataset_reference_repository.upsert(
                dataset_id=f"market-data-{source_id}",
                dataset_name="market_data",
                storage_format="parquet",
                storage_path=str(storage_path.parent),
                schema_version=records[0].schema_version,
                partition_strategy="ticker",
                first_observation=first_observation.isoformat(),
                last_observation=last_observation.isoformat(),
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )

            finished_at = datetime.now(timezone.utc)

            self.ingestion_run_repository.finish(
                run_id=run_id,
                status="SUCCESS",
                finished_at=finished_at.isoformat(),
                records_read=records_read,
                records_written=len(records),
                records_rejected=0,
            )

            return MarketDataIngestionResult(
                run_id=run_id,
                records_read=records_read,
                records_written=len(records),
                records_rejected=0,
                storage_path=str(storage_path),
            )

        except Exception as exc:
            finished_at = datetime.now(timezone.utc)

            self.ingestion_run_repository.finish(
                run_id=run_id,
                status="FAILED",
                finished_at=finished_at.isoformat(),
                records_read=locals().get("records_read", 0),
                records_written=0,
                records_rejected=0,
                error=str(exc),
            )

            raise
