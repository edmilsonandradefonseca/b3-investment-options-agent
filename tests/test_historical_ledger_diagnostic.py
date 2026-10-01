"""Behavioral safety checks: diagnostic must not initialize/migrate real stores."""
import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("ledger_diagnostic", Path(__file__).resolve().parents[1] / "scripts/historical_ledger_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class HistoricalLedgerDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_missing_database_is_not_created(self):
        path = self.root / "missing" / "options.sqlite3"
        result = diagnostic.inspect_database(path)
        self.assertEqual(result["status"], "MISSING")
        self.assertFalse(path.parent.exists())

    def test_old_schema_is_not_migrated_and_signed_rows_are_inspected(self):
        path = self.root / "options.sqlite3"
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE option_transactions (transaction_id TEXT, option_ticker TEXT, quantity REAL, average_cost REAL, total_cost REAL, as_of TEXT, secret TEXT)")
            conn.executemany("INSERT INTO option_transactions VALUES (?,?,?,?,?,?,?)", [
                ("s1", "PETRA100", -100, 2, -200, "2026-01-02", "DO_NOT_PRINT"),
                ("b1", "PETRA100", 100, 1, 100, "2026-01-10", "DO_NOT_PRINT"),
                ("p1", "RENTP100", -200, None, None, None, "DO_NOT_PRINT"),
            ])
        before = path.read_bytes()
        result = diagnostic.inspect_database(path)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(result["status"], "READ_OK")
        table = result["tables"]["option_transactions"]
        self.assertEqual(table["canonical_uc07_usable_rows"], 2)
        self.assertEqual(table["petr4_exact_rows"], 0)
        self.assertEqual(table["petr_prefix_rows_underlying_unverified"], 2)
        self.assertEqual(table["quantity_sign_counts"], {"NEGATIVE": 2, "POSITIVE": 1})
        self.assertEqual(table["date_coverage"]["as_of"]["null_count"], 1)
        self.assertEqual(table["symbol_type_hints_not_contract_metadata"], {"CALL_LETTER_HINT": 2, "PUT_LETTER_HINT": 1})
        self.assertNotIn("DO_NOT_PRINT", str(result))
        self.assertNotIn("fingerprint", [column["name"] for column in table["schema"]])

    def test_reads_committed_wal_without_checkpoint_or_migration(self):
        path = self.root / "options.sqlite3"
        conn = sqlite3.connect(path)
        self.addCleanup(conn.close)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute('CREATE TABLE "odd""table" (id INTEGER)')
        conn.execute('INSERT INTO "odd""table" VALUES (7)')
        conn.commit()
        before = path.read_bytes()
        wal = Path(str(path) + "-wal")
        before_wal = wal.read_bytes()
        result = diagnostic.inspect_database(path)
        self.assertEqual(result["tables"]['odd"table']["row_count"], 1)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(wal.read_bytes(), before_wal)

    def test_corruption_is_unknown_not_empty(self):
        path = self.root / "options.sqlite3"
        path.write_bytes(b"not a sqlite database")
        result = diagnostic.inspect_database(path)
        self.assertEqual(result["status"], "READ_ERROR")
        self.assertEqual(result["tables"], {})

    def test_canonical_path_precedence_and_no_credentials_output(self):
        env_file = self.root / "runtime.env"
        env_file.write_text(f'B3_AGENT_DATA_DIR="{self.root}/runtime"\nAPI_KEY=DO_NOT_PRINT\n')
        with patch.dict(os.environ, {}, clear=True), patch.object(diagnostic, "RUNTIME_ENV_FILES", (env_file,)):
            self.assertEqual(diagnostic._canonical_data_dir(), self.root / "runtime")
            self.assertNotIn("API_KEY", diagnostic._env_file_values(env_file))
            with patch.dict(os.environ, {"B3_AGENT_DATA_DIR": str(self.root / "override")}):
                self.assertEqual(diagnostic._canonical_data_dir(), self.root / "override")

    def test_report_does_not_promote_other_ledger_to_canonical(self):
        other = self.root / "other"
        other.mkdir()
        with sqlite3.connect(other / "options.sqlite3") as conn:
            conn.execute("CREATE TABLE option_transactions (quantity REAL)")
        canonical = self.root / "canonical"
        with patch.object(diagnostic, "_candidate_data_dirs", return_value=(canonical, other)):
            result = diagnostic.build_report(canonical)
        self.assertEqual(result["diagnosis"], "LEDGER_EXISTS_OUTSIDE_CANONICAL_DATA_DIR")
        self.assertIsNone(result["canonical_uc07_usable_rows"])
        self.assertFalse(canonical.exists())


if __name__ == "__main__":
    unittest.main()
