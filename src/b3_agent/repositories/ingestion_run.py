from b3_agent.storage.sqlite import SQLiteStore


class IngestionRunRepository:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def create(
        self,
        run_id: str,
        source_id: str,
        dataset: str,
        started_at: str,
    ) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO ingestion_runs (
                    run_id, source_id, dataset, started_at, status
                )
                VALUES (?, ?, ?, ?, 'RUNNING')
                """,
                (run_id, source_id, dataset, started_at),
            )

    def finish(
        self,
        run_id: str,
        status: str,
        finished_at: str,
        records_read: int = 0,
        records_written: int = 0,
        records_rejected: int = 0,
        error: str | None = None,
    ) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_runs
                SET status = ?,
                    finished_at = ?,
                    records_read = ?,
                    records_written = ?,
                    records_rejected = ?,
                    error = ?
                WHERE run_id = ?
                """,
                (
                    status,
                    finished_at,
                    records_read,
                    records_written,
                    records_rejected,
                    error,
                    run_id,
                ),
            )

    def get_by_id(self, run_id: str):
        with self.store.connect() as connection:
            return connection.execute(
                "SELECT * FROM ingestion_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
