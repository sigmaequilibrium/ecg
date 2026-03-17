"""Wave area feature extraction for ECG beats.

Baseline strategy
-----------------
This module supports two baseline strategies:

1. ``pr_segment`` (default): use the median value inside the PR-segment window
   as an isoelectric baseline and subtract it from the beat.
2. ``local_detrend``: fit a first-order line over the beat and subtract it.

Wave areas are computed with trapezoidal integration and returned as signed and
absolute values to preserve lead polarity and also provide polarity-agnostic
magnitude features.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import math

EPSILON = 1e-9


@dataclass(frozen=True)
class BeatBoundaries:
    q_onset: int | None
    q_offset: int | None
    s_offset: int | None
    t_onset: int | None
    t_offset: int | None
    pr_onset: int | None = None
    pr_offset: int | None = None


def _is_nan(value: float | int | None) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _validate_interval(start: int | None, end: int | None, n_samples: int) -> tuple[int, int] | None:
    if _is_nan(start) or _is_nan(end):
        return None
    s = int(start)
    e = int(end)
    if s < 0 or e < 0 or s >= n_samples or e >= n_samples or s >= e:
        return None
    return s, e


def _segment(signal: list[float], start: int | None, end: int | None) -> list[float] | None:
    interval = _validate_interval(start, end, len(signal))
    if interval is None:
        return None
    s, e = interval
    seg = signal[s : e + 1]
    if any(_is_nan(v) for v in seg):
        return None
    return seg


def _median(values: list[float]) -> float:
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def _baseline(signal: list[float], boundaries: BeatBoundaries, strategy: str) -> list[float]:
    if strategy == "pr_segment":
        pr = _segment(signal, boundaries.pr_onset, boundaries.pr_offset)
        if not pr:
            return signal.copy()
        base = _median(pr)
        return [x - base for x in signal]

    if strategy == "local_detrend":
        x = [float(i) for i, y in enumerate(signal) if not _is_nan(y)]
        y = [float(v) for v in signal if not _is_nan(v)]
        if len(x) < 2:
            return signal.copy()

        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        denom = sum((xi - mean_x) ** 2 for xi in x)
        if abs(denom) < EPSILON:
            return signal.copy()

        m = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / denom
        b = mean_y - m * mean_x
        return [float(v) - (m * i + b) for i, v in enumerate(signal)]

    raise ValueError(f"Unknown baseline strategy: {strategy}")


def _trapz(values: list[float], dt: float) -> float:
    return sum((values[i] + values[i + 1]) * 0.5 * dt for i in range(len(values) - 1))


def _integrate(signal: list[float], start: int | None, end: int | None, sampling_rate_hz: float) -> tuple[float, float]:
    seg = _segment(signal, start, end)
    if seg is None or sampling_rate_hz <= 0:
        return math.nan, math.nan
    dt = 1.0 / sampling_rate_hz
    signed = _trapz(seg, dt)
    absolute = _trapz([abs(v) for v in seg], dt)
    return signed, absolute


def compute_wave_areas(records: list[dict], *, sampling_rate_hz: float, baseline_strategy: str = "pr_segment") -> list[dict]:
    rows: list[dict] = []
    for record in records:
        signal = [float(v) for v in record["signal"]]
        b = record["boundaries"]
        boundaries = b if isinstance(b, BeatBoundaries) else BeatBoundaries(**b)
        normalized = _baseline(signal, boundaries, baseline_strategy)

        area_q, area_q_abs = _integrate(normalized, boundaries.q_onset, boundaries.q_offset, sampling_rate_hz)
        area_qrs, area_qrs_abs = _integrate(normalized, boundaries.q_onset, boundaries.s_offset, sampling_rate_hz)
        area_t, area_t_abs = _integrate(normalized, boundaries.t_onset, boundaries.t_offset, sampling_rate_hz)

        area_t_plus_q = area_t + area_q if not (_is_nan(area_t) or _is_nan(area_q)) else math.nan
        area_t_plus_q_abs = area_t_abs + area_q_abs if not (_is_nan(area_t_abs) or _is_nan(area_q_abs)) else math.nan

        ratio = math.nan
        if not _is_nan(area_t_plus_q) and not _is_nan(area_qrs) and abs(area_t_plus_q) > EPSILON:
            ratio = area_qrs / area_t_plus_q

        row = {
            "beat_id": record["beat_id"],
            "lead": record["lead"],
            "baseline_strategy": baseline_strategy,
            "area_q": area_q,
            "area_q_abs": area_q_abs,
            "area_qrs": area_qrs,
            "area_qrs_abs": area_qrs_abs,
            "area_t": area_t,
            "area_t_abs": area_t_abs,
            "area_t_plus_q": area_t_plus_q,
            "area_t_plus_q_abs": area_t_plus_q_abs,
            "ratio_qrs_to_t_plus_q": ratio,
            **{f"boundary_{k}": v for k, v in asdict(boundaries).items()},
        }
        rows.append(row)
    return rows


def save_wave_areas_table(rows: list[dict], output_path: str | Path = "data/processed/areas.parquet") -> Path:
    """Save tidy rows. If parquet backends are unavailable, write CSV fallback."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Without third-party dependencies, write CSV fallback by default.
    if target.suffix != ".csv":
        target = target.with_suffix(".csv")

    if not rows:
        target.write_text("")
        return target

    fieldnames = list(rows[0].keys())
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return target
