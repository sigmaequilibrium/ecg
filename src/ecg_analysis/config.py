from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Sequence


@dataclass(frozen=True)
class PTBXLConfig:
    """Configuration for PTB-XL(+) data loading and split handling."""

    root: Path
    metadata_csv: str = "ptbxl_database.csv"
    statements_csv: str | None = "scp_statements.csv"
    beats_csv: str | None = None
    # PTB-XL folds are 1..10; default split mirrors common usage.
    split_map: Dict[str, Sequence[int]] = field(
        default_factory=lambda: {
            "train": (1, 2, 3, 4, 5, 6, 7, 8),
            "val": (9,),
            "test": (10,),
        }
    )

    @property
    def metadata_path(self) -> Path:
        return self.root / self.metadata_csv

    @property
    def statements_path(self) -> Path | None:
        return self.root / self.statements_csv if self.statements_csv else None

    @property
    def beats_path(self) -> Path | None:
        return self.root / self.beats_csv if self.beats_csv else None
