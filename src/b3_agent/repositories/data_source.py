from b3_agent.storage.sqlite import SQLiteStore


class DataSourceRepository:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def upsert(
        self,
        source_id: str,
        name: str,
        provider_type: str,
        base_url: str | None = None,
        active: bool = True,
    ) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO data_sources (
                    source_id, name, provider_type, base_url, active
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    name = excluded.name,
                    provider_type = excluded.provider_type,
                    base_url = excluded.base_url,
                    active = excluded.active
                """,
                (
                    source_id,
                    name,
                    provider_type,
                    base_url,
                    int(active),
                ),
            )

    def get_by_id(self, source_id: str):
        with self.store.connect() as connection:
            return connection.execute(
                "SELECT * FROM data_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()

    def get_by_name(self, name: str):
        with self.store.connect() as connection:
            return connection.execute(
                "SELECT * FROM data_sources WHERE name = ?",
                (name,),
            ).fetchone()
