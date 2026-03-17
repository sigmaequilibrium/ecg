import sqlite3

from ecg_analysis.db import initialize_database


def test_initialize_database_creates_schema(tmp_path):
    db_path = initialize_database(tmp_path / "test.db")

    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "runs" in tables
        assert "wave_metrics" in tables

        indexes = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        assert "idx_wave_metrics_run_id" in indexes
        assert "idx_wave_metrics_beat_lead" in indexes
