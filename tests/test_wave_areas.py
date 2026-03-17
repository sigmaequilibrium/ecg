import math

from ecg_analysis.features.wave_areas import BeatBoundaries, _integrate, _segment, compute_wave_areas


def test_segment_returns_none_for_missing_boundaries():
    signal = [0.0, 1.0, 2.0]
    assert _segment(signal, None, 2) is None
    assert _segment(signal, 0, None) is None


def test_segment_returns_none_for_inverted_bounds():
    signal = [0.0, 1.0, 2.0, 3.0]
    assert _segment(signal, 3, 1) is None


def test_segment_returns_none_for_nan_values_in_interval():
    signal = [0.0, float("nan"), 2.0]
    assert _segment(signal, 0, 2) is None


def test_integrate_returns_nan_for_bad_interval():
    signal = [0.0, 1.0, 2.0]
    signed, absolute = _integrate(signal, 2, 1, sampling_rate_hz=100.0)
    assert math.isnan(signed)
    assert math.isnan(absolute)


def test_compute_wave_areas_zero_guard_ratio():
    records = [
        {
            "beat_id": "b1",
            "lead": "I",
            "signal": [0.0, 0.0, 0.0, 0.0, 0.0],
            "boundaries": BeatBoundaries(
                q_onset=0,
                q_offset=1,
                s_offset=2,
                t_onset=3,
                t_offset=4,
                pr_onset=0,
                pr_offset=1,
            ),
        }
    ]

    rows = compute_wave_areas(records, sampling_rate_hz=100.0)
    assert math.isnan(rows[0]["ratio_qrs_to_t_plus_q"])


def test_compute_wave_areas_signed_and_absolute_metrics():
    records = [
        {
            "beat_id": "b2",
            "lead": "V1",
            "signal": [0.0, -1.0, -0.5, 0.0, 1.0, 0.5],
            "boundaries": {
                "q_onset": 1,
                "q_offset": 2,
                "s_offset": 3,
                "t_onset": 3,
                "t_offset": 5,
                "pr_onset": 0,
                "pr_offset": 0,
            },
        }
    ]

    rows = compute_wave_areas(records, sampling_rate_hz=2.0)
    row = rows[0]

    for col in [
        "area_q",
        "area_q_abs",
        "area_qrs",
        "area_qrs_abs",
        "area_t",
        "area_t_abs",
        "area_t_plus_q",
        "area_t_plus_q_abs",
        "ratio_qrs_to_t_plus_q",
    ]:
        assert col in row

    assert row["area_q_abs"] >= abs(row["area_q"])


def test_save_wave_areas_table_writes_csv_fallback(tmp_path):
    from ecg_analysis.features.wave_areas import save_wave_areas_table

    rows = [{"beat_id": "b1", "lead": "I", "area_q": 0.1}]
    out = save_wave_areas_table(rows, tmp_path / "areas.parquet")
    assert out.suffix == ".csv"
    assert out.exists()
