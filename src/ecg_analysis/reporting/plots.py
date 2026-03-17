from __future__ import annotations

from pathlib import Path


def _scale_points(signal: list[float], start: int, end: int, width: int = 900, height: int = 300) -> list[tuple[float, float]]:
    segment = signal[start : end + 1]
    ymin, ymax = min(segment), max(segment)
    yrange = ymax - ymin if ymax > ymin else 1.0
    points = []
    for i, val in enumerate(segment):
        x = (i / max(1, len(segment) - 1)) * width
        y = height - ((val - ymin) / yrange) * height
        points.append((x, y))
    return points


def plot_beat_area_overlay(signal: list[float], beat_row: dict[str, int], lead: str, metrics_row: dict[str, float | int | str], out_path: Path) -> None:
    q_onset = beat_row["q_onset"]
    t_offset = beat_row["t_offset"]
    start = max(0, q_onset - 40)
    end = min(len(signal) - 1, t_offset + 40)
    points = _scale_points(signal, start, end)
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    title = f"Lead {lead} Beat {beat_row['beat_index']}"
    summary = (
        f"QRS={float(metrics_row['area_qrs_signed']):.3f} | "
        f"T+Q={float(metrics_row['area_t_plus_q_signed']):.3f} | "
        f"ratio={float(metrics_row['ratio_qrs_to_t_plus_q_signed']):.3f}"
    )

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='980' height='420'>
<rect width='100%' height='100%' fill='white'/>
<text x='10' y='20' font-size='18'>{title}</text>
<text x='10' y='42' font-size='14'>{summary}</text>
<polyline fill='none' stroke='black' stroke-width='1.5' points='{path}' transform='translate(40,80)'/>
<line x1='40' y1='230' x2='940' y2='230' stroke='#888' stroke-width='1'/>
</svg>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")


def plot_distributions(rows: list[dict[str, float | int | str]], out_path: Path) -> None:
    ratios = [float(r["ratio_qrs_to_t_plus_q_abs"]) for r in rows if str(r["ratio_qrs_to_t_plus_q_abs"]) != "nan"]
    if not ratios:
        out_path.write_text("No ratios available", encoding="utf-8")
        return
    bins = 20
    lo, hi = min(ratios), max(ratios)
    width = (hi - lo) / bins if hi > lo else 1.0
    counts = [0] * bins
    for r in ratios:
        idx = min(bins - 1, int((r - lo) / width))
        counts[idx] += 1

    max_count = max(counts) or 1
    bars = []
    for i, c in enumerate(counts):
        x = 40 + i * 40
        h = (c / max_count) * 260
        y = 320 - h
        bars.append(f"<rect x='{x}' y='{y:.1f}' width='30' height='{h:.1f}' fill='#6a3d9a'/>")

    svg = "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='360'><rect width='100%' height='100%' fill='white'/><text x='10' y='20' font-size='16'>Ratio QRS/(T+Q) abs distribution</text>" + "".join(bars) + "</svg>"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
