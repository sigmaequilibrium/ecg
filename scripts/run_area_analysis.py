#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from ecg_analysis.data import load_metadata, load_record
from ecg_analysis.features.wave_areas import compute_wave_areas_for_record
from ecg_analysis.reporting.plots import plot_beat_area_overlay, plot_distributions
from ecg_analysis.reporting.stats import descriptive_stats


def create_demo_dataset(data_dir: Path) -> None:
    (data_dir / "signals").mkdir(parents=True, exist_ok=True)
    leads = ["I", "II", "V1"]
    n = 1000

    signal = [[0.03 * math.sin(i / 25.0)] * len(leads) for i in range(n)]
    starts = [180, 420, 680]
    beats = []

    for beat_idx, q in enumerate(starts):
        q_offset, r, s = q + 8, q + 14, q + 22
        t_on, t_off = q + 40, q + 78
        p_end = q - 15
        beats.append(
            {
                "record_id": "demo_001",
                "beat_index": beat_idx,
                "p_end": p_end,
                "q_onset": q,
                "q_offset": q_offset,
                "s_offset": s,
                "t_onset": t_on,
                "t_offset": t_off,
            }
        )

        for li in range(len(leads)):
            polarity = -1.0 if li == 2 else 1.0
            for i in range(q, q_offset + 1):
                signal[i][li] += -0.08 * polarity
            for i in range(q_offset, r + 1):
                signal[i][li] += (i - q_offset) / (r - q_offset + 1) * 0.9
            for i in range(r, s + 1):
                signal[i][li] += (1 - (i - r) / (s - r + 1)) * 0.9 - 0.25
            for i in range(t_on, t_off + 1):
                phase = (i - t_on) / max(1, (t_off - t_on))
                signal[i][li] += polarity * math.sin(math.pi * phase) * 0.28

    with (data_dir / "signals" / "demo_001.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerows(signal)

    with (data_dir / "metadata.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["record_id", "split", "fs", "leads"])
        w.writeheader()
        w.writerow({"record_id": "demo_001", "split": "train", "fs": 500, "leads": ",".join(leads)})

    with (data_dir / "delineations.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["record_id", "beat_index", "p_end", "q_onset", "q_offset", "s_offset", "t_onset", "t_offset"])
        w.writeheader()
        w.writerows(beats)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/ptbxl_plus"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        create_demo_dataset(args.data_dir)

    metadata = load_metadata(args.data_dir)
    all_rows: list[dict] = []

    for meta_row in metadata:
        rec = load_record(meta_row["record_id"], metadata, args.data_dir)
        rows = compute_wave_areas_for_record(rec.record_id, rec.split, rec.leads, rec.signal, rec.beats)
        all_rows.extend(rows)

        first_beat = rec.beats[0]
        for lead_idx, lead in enumerate(rec.leads):
            lead_signal = [sample[lead_idx] for sample in rec.signal]
            m = [r for r in rows if r["beat_index"] == first_beat["beat_index"] and r["lead"] == lead][0]
            plot_beat_area_overlay(
                signal=lead_signal,
                beat_row=first_beat,
                lead=lead,
                metrics_row=m,
                out_path=args.output_dir / "figures" / f"overlay_{rec.record_id}_beat0_{lead}.svg",
            )

    stats_rows = descriptive_stats(all_rows)
    write_csv(args.processed_dir / "areas.csv", all_rows)
    write_csv(args.output_dir / "tables" / "descriptive_stats.csv", stats_rows)
    plot_distributions(all_rows, args.output_dir / "figures" / "ratio_distribution.svg")

    print(f"Saved {len(all_rows)} area rows")


if __name__ == "__main__":
    main()
