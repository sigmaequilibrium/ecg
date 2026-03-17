#!/usr/bin/env python3
"""Run ECG area reporting pipeline: plots, stats tables, and markdown summary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ecg_analysis.reporting.plots import generate_aggregate_plots, plot_beat_diagnostics
from ecg_analysis.reporting.stats import (
    compute_descriptive_stats,
    compute_ratio_confidence_intervals,
    export_markdown_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--beat-samples-csv",
        type=Path,
        required=True,
        help="CSV with per-sample beat waveforms and integration windows.",
    )
    parser.add_argument(
        "--beat-metrics-csv",
        type=Path,
        required=True,
        help="CSV with one row per beat containing area and ratio metrics.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="Output reports root directory.",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=1000,
        help="Number of bootstrap samples used for ratio confidence intervals.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    beat_samples = pd.read_csv(args.beat_samples_csv)
    beat_metrics = pd.read_csv(args.beat_metrics_csv)

    figures_dir = args.reports_dir / "figures"
    tables_dir = args.reports_dir / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    plot_beat_diagnostics(beat_samples, figures_dir / "beat_diagnostics")
    aggregate_paths = generate_aggregate_plots(beat_metrics, figures_dir)

    stats_df = compute_descriptive_stats(beat_metrics)
    stats_path = tables_dir / "descriptive_stats.csv"
    stats_df.to_csv(stats_path, index=False)

    ci_df = compute_ratio_confidence_intervals(
        beat_metrics,
        n_bootstrap=args.bootstrap_samples,
    )
    ci_path = tables_dir / "ratio_bootstrap_ci.csv"
    ci_df.to_csv(ci_path, index=False)

    summary_path = export_markdown_summary(
        stats_df=stats_df,
        ci_df=ci_df,
        figures=aggregate_paths,
        output_path=args.reports_dir / "summary.md",
    )

    print("Report generation complete.")
    print(f"Stats table: {stats_path}")
    print(f"Ratio CI table: {ci_path}")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
