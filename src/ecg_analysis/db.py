from __future__ import annotations

import sqlite3
from pathlib import Path


DEFAULT_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dataset_root TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS wave_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    beat_id TEXT NOT NULL,
    lead TEXT NOT NULL,
    baseline_strategy TEXT NOT NULL,
    area_q REAL,
    area_qrs REAL,
    area_t REAL,
    area_t_plus_q REAL,
    ratio_qrs_to_t_plus_q REAL,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wave_metrics_run_id ON wave_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_wave_metrics_beat_lead ON wave_metrics(beat_id, lead);
"""


def initialize_database(db_path: str | Path) -> Path:
    target = Path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(target) as conn:
        conn.executescript(DEFAULT_SCHEMA)
        conn.commit()

    return target
