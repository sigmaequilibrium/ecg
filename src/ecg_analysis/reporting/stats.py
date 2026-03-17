from __future__ import annotations

import math
from statistics import mean, median


METRICS = [
    "area_q_signed",
    "area_q_abs",
    "area_qrs_signed",
    "area_qrs_abs",
    "area_t_signed",
    "area_t_abs",
    "area_t_plus_q_signed",
    "area_t_plus_q_abs",
    "ratio_qrs_to_t_plus_q_signed",
    "ratio_qrs_to_t_plus_q_abs",
]


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    data = sorted(values)
    pos = (len(data) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return data[lo]
    return data[lo] + (data[hi] - data[lo]) * (pos - lo)


def descriptive_stats(rows: list[dict[str, float | int | str]]) -> list[dict[str, float | str | int]]:
    grouped: dict[tuple[str, str], list[dict[str, float | int | str]]] = {}
    for row in rows:
        key = (str(row["split"]), str(row["lead"]))
        grouped.setdefault(key, []).append(row)

    out: list[dict[str, float | str | int]] = []
    for (split, lead), group in grouped.items():
        for metric in METRICS:
            vals = [float(r[metric]) for r in group if not math.isnan(float(r[metric]))]
            if not vals:
                continue
            mu = mean(vals)
            std = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
            out.append(
                {
                    "split": split,
                    "lead": lead,
                    "metric": metric,
                    "count": len(vals),
                    "mean": mu,
                    "std": std,
                    "min": min(vals),
                    "q25": _percentile(vals, 0.25),
                    "median": median(vals),
                    "q75": _percentile(vals, 0.75),
                    "max": max(vals),
                }
            )
    return out
