# ECG Beat/Lead Wave Area Analysis

This project runs beat-level and lead-level ECG area analysis for the hypothesis:

- `QRS area ~ T area + Q area`
- ratio: `QRS / (T + Q)`

It includes:
- per-beat/per-lead area extraction (`Q`, `QRS`, `T`, `T+Q`), signed and absolute
- descriptive statistics by `split` and `lead`
- visualization outputs as SVG overlays and a ratio histogram

## Expected data layout

Under `data/ptbxl_plus` (or your `--data-dir`):

- `metadata.csv`
  - `record_id,split,fs,leads`
- `delineations.csv`
  - `record_id,beat_index,p_end,q_onset,q_offset,s_offset,t_onset,t_offset`
- `signals/<record_id>.csv`
  - signal matrix with rows as samples and columns as leads

## Run demo

```bash
python scripts/run_area_analysis.py --demo
```

## Run with your dataset

```bash
python scripts/run_area_analysis.py --data-dir data/ptbxl_plus
```

## Outputs

- `data/processed/areas.csv`
- `reports/tables/descriptive_stats.csv`
- `reports/figures/overlay_*.svg`
- `reports/figures/ratio_distribution.svg`
