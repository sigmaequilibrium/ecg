#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from ecg_analysis.db import initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize ECG analysis SQLite database")
    parser.add_argument("--db-path", type=Path, default=Path("data/ecg_analysis.db"))
    args = parser.parse_args()

    path = initialize_database(args.db_path)
    print(f"Initialized database at: {path}")


if __name__ == "__main__":
    main()
