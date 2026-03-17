from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from ecg_analysis.reporting.stats import (  # noqa: E402
    compute_descriptive_stats,
    compute_ratio_confidence_intervals,
    export_markdown_summary,
)


def test_compute_descriptive_stats_groups_and_percentiles():
    frame = pd.DataFrame(
        {
            "dataset_split": ["train", "train", "test"],
            "lead": ["I", "I", "V1"],
            "area_q": [1.0, 3.0, 2.0],
            "area_qrs": [2.0, 4.0, 2.5],
            "area_t": [1.0, 1.5, 1.25],
            "area_t_plus_q": [2.0, 4.5, 3.25],
            "ratio_tq_qrs": [0.5, 0.9, 1.2],
        }
    )

    result = compute_descriptive_stats(frame, metrics=["ratio_tq_qrs"], percentiles=[0.5])
    train_i = result[(result["dataset_split"] == "train") & (result["lead"] == "I")].iloc[0]
    assert train_i["n"] == 2
    assert train_i["mean"] == pytest.approx(0.7)
    assert train_i["p50"] == pytest.approx(0.7)


def test_compute_descriptive_stats_validates_required_columns():
    frame = pd.DataFrame({"lead": ["I"], "ratio_tq_qrs": [1.0]})
    with pytest.raises(ValueError, match="Missing required columns"):
        compute_descriptive_stats(frame, metrics=["ratio_tq_qrs"])


def test_compute_ratio_confidence_intervals_returns_expected_schema():
    frame = pd.DataFrame(
        {
            "dataset_split": ["train", "train", "train", "test"],
            "lead": ["I", "I", "I", "V1"],
            "ratio_tq_qrs": [0.5, 0.7, 0.9, 1.1],
        }
    )

    result = compute_ratio_confidence_intervals(frame, n_bootstrap=200, random_seed=123)
    row = result[(result["dataset_split"] == "train") & (result["lead"] == "I")].iloc[0]
    assert row["n"] == 3
    assert row["ci_low"] <= row["mean"] <= row["ci_high"]


def test_export_markdown_summary_writes_sections(tmp_path):
    stats_df = pd.DataFrame(
        [{"dataset_split": "train", "lead": "I", "metric": "ratio_tq_qrs", "mean": 0.8, "median": 0.75, "iqr": 0.1, "n": 12}]
    )
    ci_df = pd.DataFrame(
        [{"dataset_split": "train", "lead": "I", "mean": 0.8, "confidence": 0.95, "ci_low": 0.7, "ci_high": 0.9}]
    )

    output = export_markdown_summary(stats_df, ci_df, {"ratio_plot": Path("reports/ratio_plot.png")}, tmp_path / "summary.md")
    text = output.read_text(encoding="utf-8")

    assert "# ECG Area Reporting Summary" in text
    assert "Top 5 dataset split / lead groups by mean ratio(T+Q)/QRS" in text
    assert "`ratio_plot`: `reports/ratio_plot.png`" in text
