"""Statistics and report-export utilities for ECG area reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


DEFAULT_PERCENTILES: tuple[float, ...] = (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)


def _iqr(values: pd.Series) -> float:
    return float(values.quantile(0.75) - values.quantile(0.25))


def compute_descriptive_stats(
    frame: pd.DataFrame,
    metrics: Sequence[str] | None = None,
    percentiles: Sequence[float] = DEFAULT_PERCENTILES,
) -> pd.DataFrame:
    """Compute descriptive statistics by lead and dataset split."""

    if metrics is None:
        metrics = ["area_q", "area_qrs", "area_t", "area_t_plus_q", "ratio_tq_qrs"]

    required = {"lead", "dataset_split", *metrics}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    rows: list[dict[str, object]] = []
    grouped = frame.groupby(["dataset_split", "lead"], dropna=False)
    for (dataset_split, lead), group in grouped:
        for metric in metrics:
            values = group[metric].dropna()
            if values.empty:
                continue
            row: dict[str, object] = {
                "dataset_split": dataset_split,
                "lead": lead,
                "metric": metric,
                "n": int(values.shape[0]),
                "mean": float(values.mean()),
                "std": float(values.std(ddof=1)) if values.shape[0] > 1 else np.nan,
                "median": float(values.median()),
                "iqr": _iqr(values),
                "min": float(values.min()),
                "max": float(values.max()),
            }
            for p in percentiles:
                label = f"p{int(round(p * 100)):02d}"
                row[label] = float(values.quantile(p))
            rows.append(row)

    return pd.DataFrame(rows)


def compute_ratio_confidence_intervals(
    frame: pd.DataFrame,
    ratio_column: str = "ratio_tq_qrs",
    group_columns: Iterable[str] = ("dataset_split", "lead"),
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    random_seed: int = 7,
) -> pd.DataFrame:
    """Estimate bootstrap confidence intervals for a ratio metric."""

    required = set(group_columns) | {ratio_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    alpha = (1.0 - confidence) / 2.0
    rng = np.random.default_rng(random_seed)
    rows: list[dict[str, object]] = []

    grouped = frame.groupby(list(group_columns), dropna=False)
    for keys, group in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        values = group[ratio_column].dropna().to_numpy(dtype=float)
        if values.size == 0:
            continue

        means = np.empty(n_bootstrap, dtype=float)
        for i in range(n_bootstrap):
            sample = rng.choice(values, size=values.size, replace=True)
            means[i] = np.nanmean(sample)

        low, high = np.quantile(means, [alpha, 1.0 - alpha])
        row = {col: keys[idx] for idx, col in enumerate(group_columns)}
        row.update(
            {
                "metric": ratio_column,
                "n": int(values.size),
                "mean": float(np.nanmean(values)),
                "ci_low": float(low),
                "ci_high": float(high),
                "confidence": float(confidence),
                "bootstrap_samples": int(n_bootstrap),
            }
        )
        rows.append(row)

    return pd.DataFrame(rows)


def export_markdown_summary(
    stats_df: pd.DataFrame,
    ci_df: pd.DataFrame,
    figures: dict[str, Path],
    output_path: str | Path,
    caveats: Sequence[str] | None = None,
) -> Path:
    """Write a markdown summary with key findings and caveats."""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    caveat_lines = caveats or [
        "Area estimates depend on segmentation boundaries and waveform preprocessing.",
        "Bootstrap confidence intervals summarize sampling uncertainty only.",
        "Comparisons across leads/splits may be influenced by class and beat-morphology imbalance.",
    ]

    top_ratios = (
        stats_df[stats_df["metric"] == "ratio_tq_qrs"]
        .sort_values("mean", ascending=False)
        .head(5)
    )

    with out.open("w", encoding="utf-8") as handle:
        handle.write("# ECG Area Reporting Summary\n\n")
        handle.write("## Key findings\n\n")
        if top_ratios.empty:
            handle.write("No ratio statistics were available.\n\n")
        else:
            handle.write("Top 5 dataset split / lead groups by mean ratio(T+Q)/QRS:\n\n")
            for _, row in top_ratios.iterrows():
                handle.write(
                    f"- `{row['dataset_split']}` / `{row['lead']}`: "
                    f"mean={row['mean']:.4f}, median={row['median']:.4f}, IQR={row['iqr']:.4f} (n={int(row['n'])})\n"
                )
            handle.write("\n")

        if not ci_df.empty:
            handle.write("## Ratio confidence intervals\n\n")
            for _, row in ci_df.iterrows():
                handle.write(
                    f"- `{row['dataset_split']}` / `{row['lead']}`: "
                    f"mean={row['mean']:.4f}, {int(row['confidence']*100)}% CI "
                    f"[{row['ci_low']:.4f}, {row['ci_high']:.4f}]\n"
                )
            handle.write("\n")

        handle.write("## Generated figures\n\n")
        for name, path in sorted(figures.items()):
            handle.write(f"- `{name}`: `{path.as_posix()}`\n")
        handle.write("\n")

        handle.write("## Caveats\n\n")
        for item in caveat_lines:
            handle.write(f"- {item}\n")

    return out
