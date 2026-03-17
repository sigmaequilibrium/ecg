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


## Install scripts

This repository includes install/setup helpers in `scripts/`.

### `scripts/install.sh` (recommended)

Use the setup script to create a local virtualenv, install the package in editable mode,
create common project directories, and initialize a SQLite database used for analysis runs:

```bash
bash scripts/install.sh
```

Optional environment overrides:

- `VENV_DIR`: where to create the virtualenv (default: `.venv`)
- `DB_PATH`: SQLite database path (default: `data/ecg_analysis.db`)

Example with custom paths:

```bash
VENV_DIR=$HOME/.venvs/ecg DB_PATH=$PWD/data/local.db bash scripts/install.sh
```

### `scripts/init_db.py` (database only)

If your Python environment is already set up, you can initialize only the SQLite database:

```bash
PYTHONPATH=src python scripts/init_db.py --db-path data/ecg_analysis.db
```
