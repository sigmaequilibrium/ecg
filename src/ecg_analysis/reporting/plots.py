"""Plotting utilities for ECG area-based reporting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "beat_id",
    "lead",
    "dataset_split",
    "fold",
    "time",
    "signal",
    "q_start",
    "q_end",
    "qrs_start",
    "qrs_end",
    "t_start",
    "t_end",
    "area_q",
    "area_qrs",
    "area_t",
    "area_t_plus_q",
    "ratio_tq_qrs",
}


@dataclass(frozen=True)
class SegmentWindow:
    """Integration window metadata for annotation and plotting."""

    start_col: str
    end_col: str
    color: str
    label: str


SEGMENTS: tuple[SegmentWindow, ...] = (
    SegmentWindow("q_start", "q_end", "#7fb3d5", "Q"),
    SegmentWindow("qrs_start", "qrs_end", "#82e0aa", "QRS"),
    SegmentWindow("t_start", "t_end", "#f5b7b1", "T"),
)


def _validate_columns(frame: pd.DataFrame, required: Iterable[str]) -> None:
    missing = set(required) - set(frame.columns)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns: {missing_str}")


def _plot_segment_area(
    ax: plt.Axes,
    times: np.ndarray,
    signal: np.ndarray,
    start: float,
    end: float,
    color: str,
    label: str,
) -> None:
    mask = (times >= start) & (times <= end)
    if not np.any(mask):
        return
    ax.fill_between(times[mask], signal[mask], 0.0, alpha=0.3, color=color, label=f"{label} area")
    ax.axvline(start, color=color, linestyle="--", linewidth=1)
    ax.axvline(end, color=color, linestyle=":", linewidth=1)


def plot_beat_diagnostics(
    beat_frame: pd.DataFrame,
    output_dir: str | Path,
    dpi: int = 160,
) -> list[Path]:
    """Generate beat-level diagnostic plots per lead.

    Expects a long-format dataframe where each row is a sample in one beat and all
    area/ratio fields are repeated for that beat.
    """

    _validate_columns(beat_frame, REQUIRED_COLUMNS)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for (lead, beat_id), beat in beat_frame.groupby(["lead", "beat_id"], sort=False):
        beat = beat.sort_values("time")
        times = beat["time"].to_numpy(dtype=float)
        signal = beat["signal"].to_numpy(dtype=float)
        metric_row = beat.iloc[0]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(times, signal, color="#34495e", linewidth=1.4, label="waveform")
        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.5)

        for segment in SEGMENTS:
            _plot_segment_area(
                ax=ax,
                times=times,
                signal=signal,
                start=float(metric_row[segment.start_col]),
                end=float(metric_row[segment.end_col]),
                color=segment.color,
                label=segment.label,
            )

        text = (
            f"Q={metric_row['area_q']:.4f}\n"
            f"QRS={metric_row['area_qrs']:.4f}\n"
            f"T={metric_row['area_t']:.4f}\n"
            f"T+Q={metric_row['area_t_plus_q']:.4f}\n"
            f"ratio(T+Q)/QRS={metric_row['ratio_tq_qrs']:.4f}"
        )
        ax.text(
            0.99,
            0.98,
            text,
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
        )

        ax.set_title(f"Beat diagnostic - lead {lead}, beat {beat_id}")
        ax.set_xlabel("Time")
        ax.set_ylabel("Amplitude")
        ax.legend(loc="lower left", ncol=2, fontsize=8)
        fig.tight_layout()

        path = output_root / f"beat_diagnostic_lead-{lead}_beat-{beat_id}.png"
        fig.savefig(path, dpi=dpi)
        plt.close(fig)
        paths.append(path)

    return paths


def generate_aggregate_plots(
    metrics_frame: pd.DataFrame,
    output_dir: str | Path,
    dpi: int = 160,
) -> dict[str, Path]:
    """Generate aggregate plots of areas/ratios grouped by lead and data partition."""

    required = {
        "lead",
        "dataset_split",
        "fold",
        "area_q",
        "area_qrs",
        "area_t",
        "area_t_plus_q",
        "ratio_tq_qrs",
    }
    _validate_columns(metrics_frame, required)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    plots: dict[str, Path] = {}

    # Distributions by lead and split.
    measure_columns = ["area_q", "area_qrs", "area_t", "area_t_plus_q", "ratio_tq_qrs"]
    melted = metrics_frame.melt(
        id_vars=["lead", "dataset_split", "fold"],
        value_vars=measure_columns,
        var_name="metric",
        value_name="value",
    )

    for kind in ("box", "violin", "hist"):
        if kind == "hist":
            fig, axes = plt.subplots(1, len(measure_columns), figsize=(4 * len(measure_columns), 4), sharey=False)
            for idx, metric in enumerate(measure_columns):
                ax = axes[idx]
                subset = melted[melted["metric"] == metric]
                for split, split_df in subset.groupby("dataset_split"):
                    ax.hist(split_df["value"], bins=20, alpha=0.45, label=str(split), density=False)
                ax.set_title(metric)
                ax.set_xlabel("Value")
                if idx == 0:
                    ax.set_ylabel("Count")
            axes[-1].legend(title="dataset_split", fontsize=8)
            fig.tight_layout()
        else:
            fig, axes = plt.subplots(len(measure_columns), 1, figsize=(12, 3 * len(measure_columns)))
            for ax, metric in zip(axes, measure_columns, strict=True):
                subset = melted[melted["metric"] == metric]
                lead_order = sorted(subset["lead"].unique())
                split_order = sorted(subset["dataset_split"].unique())
                positions = np.arange(len(lead_order))
                width = 0.8 / max(len(split_order), 1)

                for i, split in enumerate(split_order):
                    split_data = [
                        subset[(subset["lead"] == lead) & (subset["dataset_split"] == split)]["value"].dropna().to_numpy()
                        for lead in lead_order
                    ]
                    if kind == "box":
                        bp = ax.boxplot(
                            split_data,
                            positions=positions + i * width,
                            widths=width * 0.9,
                            patch_artist=True,
                            manage_ticks=False,
                            medianprops={"color": "black", "linewidth": 1},
                        )
                        color = plt.cm.Set2(i / max(len(split_order), 1))
                        for box in bp["boxes"]:
                            box.set_facecolor(color)
                            box.set_alpha(0.7)
                    else:
                        parts = ax.violinplot(
                            split_data,
                            positions=positions + i * width,
                            widths=width * 0.9,
                            showmeans=False,
                            showmedians=True,
                            showextrema=False,
                        )
                        color = plt.cm.Set2(i / max(len(split_order), 1))
                        for body in parts["bodies"]:
                            body.set_facecolor(color)
                            body.set_alpha(0.6)

                ax.set_title(f"{metric} by lead and dataset_split")
                ax.set_xticks(positions + width * (len(split_order) - 1) / 2)
                ax.set_xticklabels(lead_order, rotation=0)
                ax.set_ylabel(metric)
            fig.tight_layout()

        path = output_root / f"aggregate_{kind}_by_lead_split.png"
        fig.savefig(path, dpi=dpi)
        plt.close(fig)
        plots[f"distribution_{kind}"] = path

    # Grouped by fold for ratio.
    fold_group = (
        metrics_frame.groupby(["dataset_split", "fold", "lead"], dropna=False)["ratio_tq_qrs"]
        .mean()
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(12, 5))
    for (split, lead), part in fold_group.groupby(["dataset_split", "lead"], sort=False):
        part = part.sort_values("fold")
        ax.plot(part["fold"], part["ratio_tq_qrs"], marker="o", linewidth=1.2, label=f"{split}-{lead}")
    ax.set_title("Mean ratio(T+Q)/QRS by fold")
    ax.set_xlabel("Fold")
    ax.set_ylabel("Mean ratio")
    ax.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fold_path = output_root / "aggregate_ratio_by_fold.png"
    fig.savefig(fold_path, dpi=dpi)
    plt.close(fig)
    plots["ratio_by_fold"] = fold_path

    # Scatter and correlation line.
    fig, ax = plt.subplots(figsize=(7, 6))
    x = metrics_frame["area_qrs"].to_numpy(dtype=float)
    y = metrics_frame["area_t_plus_q"].to_numpy(dtype=float)
    ax.scatter(x, y, alpha=0.45, edgecolors="none", c="#5dade2")
    coeff = np.polyfit(x, y, deg=1)
    line_x = np.linspace(np.nanmin(x), np.nanmax(x), num=100)
    line_y = np.polyval(coeff, line_x)
    corr = np.corrcoef(x, y)[0, 1] if len(x) > 1 else np.nan
    ax.plot(line_x, line_y, color="#c0392b", linewidth=2, label=f"fit: y={coeff[0]:.2f}x+{coeff[1]:.2f}")
    ax.text(0.02, 0.98, f"Pearson r={corr:.3f}", transform=ax.transAxes, ha="left", va="top")
    ax.set_title("area_qrs vs area_t_plus_q")
    ax.set_xlabel("area_qrs")
    ax.set_ylabel("area_t_plus_q")
    ax.legend(loc="lower right")
    fig.tight_layout()
    scatter_path = output_root / "scatter_area_qrs_vs_area_t_plus_q.png"
    fig.savefig(scatter_path, dpi=dpi)
    plt.close(fig)
    plots["scatter_qrs_vs_t_plus_q"] = scatter_path

    return plots
