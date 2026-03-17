from __future__ import annotations

EPS = 1e-8


def _trapz(values: list[float]) -> float:
    return sum((values[i] + values[i + 1]) / 2.0 for i in range(len(values) - 1))


def trapz_area(signal: list[float], start: int, end: int, baseline: float = 0.0, use_abs: bool = False) -> float:
    if start < 0 or end >= len(signal):
        raise ValueError("interval out of bounds")
    if end <= start:
        raise ValueError("invalid interval")
    values = [x - baseline for x in signal[start : end + 1]]
    if use_abs:
        values = [abs(v) for v in values]
    return _trapz(values)


def baseline_from_pr(signal: list[float], p_end: int, q_onset: int) -> float:
    if p_end < 0 or q_onset <= p_end:
        return 0.0
    seg = signal[p_end:q_onset]
    return sum(seg) / len(seg) if seg else 0.0


def compute_wave_areas_for_record(record_id: str, split: str, leads: list[str], signal: list[list[float]], beats: list[dict[str, int]]) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    lead_series = {lead: [sample[idx] for sample in signal] for idx, lead in enumerate(leads)}

    for beat in beats:
        for lead in leads:
            s = lead_series[lead]
            baseline = baseline_from_pr(s, beat["p_end"], beat["q_onset"])
            area_q_signed = trapz_area(s, beat["q_onset"], beat["q_offset"], baseline, False)
            area_q_abs = trapz_area(s, beat["q_onset"], beat["q_offset"], baseline, True)
            area_qrs_signed = trapz_area(s, beat["q_onset"], beat["s_offset"], baseline, False)
            area_qrs_abs = trapz_area(s, beat["q_onset"], beat["s_offset"], baseline, True)
            area_t_signed = trapz_area(s, beat["t_onset"], beat["t_offset"], baseline, False)
            area_t_abs = trapz_area(s, beat["t_onset"], beat["t_offset"], baseline, True)

            area_t_plus_q_signed = area_t_signed + area_q_signed
            area_t_plus_q_abs = area_t_abs + area_q_abs
            ratio_signed = area_qrs_signed / area_t_plus_q_signed if abs(area_t_plus_q_signed) > EPS else float("nan")
            ratio_abs = area_qrs_abs / area_t_plus_q_abs if abs(area_t_plus_q_abs) > EPS else float("nan")

            rows.append(
                {
                    "record_id": record_id,
                    "split": split,
                    "beat_index": beat["beat_index"],
                    "lead": lead,
                    "baseline": baseline,
                    "area_q_signed": area_q_signed,
                    "area_q_abs": area_q_abs,
                    "area_qrs_signed": area_qrs_signed,
                    "area_qrs_abs": area_qrs_abs,
                    "area_t_signed": area_t_signed,
                    "area_t_abs": area_t_abs,
                    "area_t_plus_q_signed": area_t_plus_q_signed,
                    "area_t_plus_q_abs": area_t_plus_q_abs,
                    "ratio_qrs_to_t_plus_q_signed": ratio_signed,
                    "ratio_qrs_to_t_plus_q_abs": ratio_abs,
                }
            )
    return rows
