from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Sequence

import pandas as pd

from ecg_analysis.config import PTBXLConfig

if TYPE_CHECKING:
    import numpy as np


@dataclass(frozen=True)
class RecordMetadata:
    record_id: int
    patient_id: int | None
    fold: int | None
    split: str
    sampling_rate: int | None
    filename_lr: str | None = None
    filename_hr: str | None = None


@dataclass(frozen=True)
class BeatAnnotation:
    """Normalized internal schema for one beat in one lead."""

    record_id: int
    beat_index: int
    lead: str
    q_onset: int | None = None
    q_offset: int | None = None
    r_peak: int | None = None
    s_offset: int | None = None
    t_onset: int | None = None
    t_offset: int | None = None


@dataclass(frozen=True)
class ValidationIssue:
    record_id: int
    beat_index: int
    lead: str
    field: str
    message: str


class PTBXLLoader:
    def __init__(self, config: PTBXLConfig) -> None:
        self.config = config

    def load_metadata(self) -> pd.DataFrame:
        """Load PTB-XL metadata CSV and add split labels from folds."""
        df = pd.read_csv(self.config.metadata_path)
        if "ecg_id" not in df.columns:
            raise ValueError("Expected `ecg_id` column in PTB-XL metadata CSV")

        if "strat_fold" in df.columns:
            fold_series = df["strat_fold"]
        else:
            fold_series = pd.Series([None] * len(df))

        df["split"] = fold_series.apply(self._fold_to_split)
        return df

    def iter_records(self, split: str | None = None) -> Iterable[RecordMetadata]:
        df = self.load_metadata()
        if split:
            df = df[df["split"] == split]

        for _, row in df.iterrows():
            yield RecordMetadata(
                record_id=int(row["ecg_id"]),
                patient_id=_optional_int(row.get("patient_id")),
                fold=_optional_int(row.get("strat_fold")),
                split=str(row.get("split", "unknown")),
                sampling_rate=_optional_int(row.get("sampling_rate")),
                filename_lr=row.get("filename_lr"),
                filename_hr=row.get("filename_hr"),
            )

    def load_record_signal(
        self,
        record: RecordMetadata,
        high_resolution: bool = True,
    ) -> tuple["np.ndarray", list[str]]:
        """Read waveform samples and lead names from WFDB records."""
        try:
            import wfdb
        except Exception as exc:  # pragma: no cover - optional dependency in minimal package
            raise ImportError("wfdb is required to read PTB-XL waveform files") from exc

        rel_path = record.filename_hr if high_resolution else record.filename_lr
        if not rel_path:
            raise ValueError("No waveform file path available for this record")

        wfdb_path = self.config.root / rel_path
        signal, fields = wfdb.rdsamp(str(wfdb_path))
        leads = list(fields.get("sig_name", []))
        return signal, leads

    def load_beat_annotations(self) -> list[BeatAnnotation]:
        """Load beat-level annotations if configured and present."""
        beats_path = self.config.beats_path
        if beats_path is None or not beats_path.exists():
            return []

        df = pd.read_csv(beats_path)
        required = {"record_id", "beat_index", "lead"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required beat annotation columns: {sorted(missing)}")

        anns: list[BeatAnnotation] = []
        for _, row in df.iterrows():
            anns.append(
                BeatAnnotation(
                    record_id=int(row["record_id"]),
                    beat_index=int(row["beat_index"]),
                    lead=str(row["lead"]),
                    q_onset=_optional_int(row.get("q_onset")),
                    q_offset=_optional_int(row.get("q_offset")),
                    r_peak=_optional_int(row.get("r_peak")),
                    s_offset=_optional_int(row.get("s_offset")),
                    t_onset=_optional_int(row.get("t_onset")),
                    t_offset=_optional_int(row.get("t_offset")),
                )
            )
        return anns

    def validate_annotations(
        self,
        annotations: Sequence[BeatAnnotation],
        signal_length_by_record: dict[int, int] | None = None,
    ) -> list[ValidationIssue]:
        """Flag missing annotations, invalid intervals, and out-of-range indices."""
        issues: list[ValidationIssue] = []

        for ann in annotations:
            for field_name in ("q_onset", "q_offset", "r_peak", "s_offset", "t_onset", "t_offset"):
                value = getattr(ann, field_name)
                if value is None:
                    issues.append(
                        ValidationIssue(
                            record_id=ann.record_id,
                            beat_index=ann.beat_index,
                            lead=ann.lead,
                            field=field_name,
                            message="missing value",
                        )
                    )
                    continue

                if value < 0:
                    issues.append(
                        ValidationIssue(
                            record_id=ann.record_id,
                            beat_index=ann.beat_index,
                            lead=ann.lead,
                            field=field_name,
                            message="negative index",
                        )
                    )

                max_len = (signal_length_by_record or {}).get(ann.record_id)
                if max_len is not None and value >= max_len:
                    issues.append(
                        ValidationIssue(
                            record_id=ann.record_id,
                            beat_index=ann.beat_index,
                            lead=ann.lead,
                            field=field_name,
                            message=f"index {value} out of range [0, {max_len - 1}]",
                        )
                    )

            issues.extend(_check_ordering(ann))

        return issues

    def _fold_to_split(self, fold: int | float | None) -> str:
        if pd.isna(fold):
            return "unknown"
        fold_int = int(fold)
        for split_name, folds in self.config.split_map.items():
            if fold_int in folds:
                return split_name
        return "unknown"


def _check_ordering(ann: BeatAnnotation) -> list[ValidationIssue]:
    ordered = [
        ("q_onset", ann.q_onset),
        ("q_offset", ann.q_offset),
        ("r_peak", ann.r_peak),
        ("s_offset", ann.s_offset),
        ("t_onset", ann.t_onset),
        ("t_offset", ann.t_offset),
    ]
    issues: list[ValidationIssue] = []

    previous_name = None
    previous_value = None
    for name, value in ordered:
        if previous_name is not None and previous_value is not None and value is not None:
            if value < previous_value:
                issues.append(
                    ValidationIssue(
                        record_id=ann.record_id,
                        beat_index=ann.beat_index,
                        lead=ann.lead,
                        field=name,
                        message=f"{name} ({value}) occurs before {previous_name} ({previous_value})",
                    )
                )
        if value is not None:
            previous_name = name
            previous_value = value

    return issues


def _optional_int(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)
