# ECG Analysis (minimal PTB-XL package)

This repository contains a minimal analysis package for loading PTB-XL(+) metadata,
waveforms, and optional beat-level annotations.

## Folder layout

Expected PTB-XL(+) files under a dataset root (for example `/data/ptbxl`):

```text
/data/ptbxl/
  ptbxl_database.csv
  scp_statements.csv                 # optional in this minimal package
  records100/...
  records500/...
  beat_annotations.csv               # optional custom/derived file
```

Where:
- `ptbxl_database.csv` is required and must include `ecg_id` plus PTB-XL fields like
  `patient_id`, `strat_fold`, `sampling_rate`, `filename_lr`, `filename_hr`.
- `beat_annotations.csv` is optional and should include at least:
  `record_id`, `beat_index`, `lead`, and any of:
  `q_onset`, `q_offset`, `r_peak`, `s_offset`, `t_onset`, `t_offset`.

## Package structure

- `src/ecg_analysis/config.py`: `PTBXLConfig` with dataset paths and split mapping.
- `src/ecg_analysis/data/ptbxl.py`: loader, normalized beat schema, and validation.
- `scripts/explore_ptbxl.py`: quick CLI summary for exploratory runs.

## Run exploratory summary

```bash
PYTHONPATH=src python scripts/explore_ptbxl.py /data/ptbxl --beats-csv beat_annotations.csv
```

This prints:
- total records,
- split distribution (from PTB-XL folds),
- annotation count,
- validation issue count and sample issues.
