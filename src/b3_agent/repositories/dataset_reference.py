from b3_agent.storage.sqlite import SQLiteStore


class DatasetReferenceRepository:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def upsert(
        self,
        dataset_id: str,
        dataset_name: str,
        storage_format: str,
        storage_path: str,
        schema_version: str,
        partition_strategy: str | None = None,
        first_observation: str | None = None,
        last_observation: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO dataset_references (
                    dataset_id,
                    dataset_name,
                    storage_format,
                    storage_path,
                    schema_version,
                    partition_strategy,
                    first_observation,
                    last_observation,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id) DO UPDATE SET
                    dataset_name = excluded.dataset_name,
                    storage_format = excluded.storage_format,
                    storage_path = excluded.storage_path,
                    schema_version = excluded.schema_version,
                    partition_strategy = excluded.partition_strategy,
                    first_observation = excluded.first_observation,
                    last_observation = excluded.last_observation,
                    updated_at = excluded.updated_at
                """,
                (
                    dataset_id,
                    dataset_name,
                    storage_format,
                    storage_path,
                    schema_version,
                    partition_strategy,
                    first_observation,
                    last_observation,
                    created_at,
                    updated_at,
                ),
            )

    def get_by_id(self, dataset_id: str):
        with self.store.connect() as connection:
            return connection.execute(
                "SELECT * FROM dataset_references WHERE dataset_id = ?",
                (dataset_id,),
            ).fetchone()

    def get_by_name(self, dataset_name: str):
        with self.store.connect() as connection:
            return connection.execute(
                "SELECT * FROM dataset_references WHERE dataset_name = ?",
                (dataset_name,),
            ).fetchone()
