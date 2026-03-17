from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadedRecord:
    record_id: str
    split: str
    leads: list[str]
    fs: float
    signal: list[list[float]]  # samples x leads
    beats: list[dict[str, int]]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_metadata(data_dir: Path) -> list[dict[str, str]]:
    metadata_path = data_dir / "metadata.csv"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata file: {metadata_path}")
    return _read_csv_rows(metadata_path)


def _read_signal_csv(path: Path) -> list[list[float]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return [[float(x) for x in row] for row in reader if row]


def load_record(record_id: str, metadata: list[dict[str, str]], data_dir: Path) -> LoadedRecord:
    rows = [r for r in metadata if r["record_id"] == record_id]
    if not rows:
        raise ValueError(f"record_id={record_id} not in metadata")
    row = rows[0]
    leads = [x.strip() for x in row["leads"].split(",") if x.strip()]

    signal_path = data_dir / "signals" / f"{record_id}.csv"
    signal = _read_signal_csv(signal_path)
    if not signal:
        raise ValueError(f"Empty signal file: {signal_path}")
    if len(signal[0]) != len(leads):
        raise ValueError("Signal lead count does not match metadata leads")

    delineations = _read_csv_rows(data_dir / "delineations.csv")
    beats: list[dict[str, int]] = []
    for d in delineations:
        if d["record_id"] != record_id:
            continue
        beats.append(
            {
                "beat_index": int(d["beat_index"]),
                "p_end": int(d["p_end"]),
                "q_onset": int(d["q_onset"]),
                "q_offset": int(d["q_offset"]),
                "s_offset": int(d["s_offset"]),
                "t_onset": int(d["t_onset"]),
                "t_offset": int(d["t_offset"]),
            }
        )
    if not beats:
        raise ValueError(f"No beats for {record_id}")

    return LoadedRecord(record_id, row["split"], leads, float(row["fs"]), signal, beats)
