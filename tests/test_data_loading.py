from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "ecg_analysis" / "data.py"
_SPEC = spec_from_file_location("ecg_analysis_data_module", MODULE_PATH)
assert _SPEC and _SPEC.loader
_data_module = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _data_module
_SPEC.loader.exec_module(_data_module)

load_metadata = _data_module.load_metadata
load_record = _data_module.load_record


def _write_csv(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_metadata_reads_metadata_csv(tmp_path):
    _write_csv(tmp_path / "metadata.csv", "record_id,split,leads,fs\nrec1,train,I,100\n")
    rows = load_metadata(tmp_path)
    assert rows == [{"record_id": "rec1", "split": "train", "leads": "I", "fs": "100"}]


def test_load_metadata_raises_when_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Missing metadata file"):
        load_metadata(tmp_path)


def test_load_record_returns_loaded_record(tmp_path):
    _write_csv(tmp_path / "metadata.csv", 'record_id,split,leads,fs\nrec1,train,"I,II",100\n')
    _write_csv(tmp_path / "signals" / "rec1.csv", "0.1,0.2\n0.3,0.4\n")
    _write_csv(
        tmp_path / "delineations.csv",
        "record_id,beat_index,p_end,q_onset,q_offset,s_offset,t_onset,t_offset\nrec1,0,1,2,3,4,5,6\n",
    )

    record = load_record("rec1", load_metadata(tmp_path), tmp_path)

    assert record.record_id == "rec1"
    assert record.split == "train"
    assert record.leads == ["I", "II"]
    assert record.fs == 100.0
    assert record.signal == [[0.1, 0.2], [0.3, 0.4]]
    assert record.beats[0]["beat_index"] == 0


def test_load_record_validates_signal_shape_and_beats(tmp_path):
    _write_csv(tmp_path / "metadata.csv", "record_id,split,leads,fs\nrec1,train,I,100\n")
    _write_csv(tmp_path / "signals" / "rec1.csv", "")
    _write_csv(tmp_path / "delineations.csv", "record_id,beat_index,p_end,q_onset,q_offset,s_offset,t_onset,t_offset\n")
    metadata = load_metadata(tmp_path)

    with pytest.raises(ValueError, match="Empty signal file"):
        load_record("rec1", metadata, tmp_path)

    _write_csv(tmp_path / "signals" / "rec1.csv", "0.1,0.2\n")
    with pytest.raises(ValueError, match="Signal lead count does not match"):
        load_record("rec1", metadata, tmp_path)

    _write_csv(tmp_path / "signals" / "rec1.csv", "0.1\n")
    with pytest.raises(ValueError, match="No beats for rec1"):
        load_record("rec1", metadata, tmp_path)


def test_load_record_raises_for_unknown_record(tmp_path):
    _write_csv(tmp_path / "metadata.csv", "record_id,split,leads,fs\nrec1,train,I,100\n")
    with pytest.raises(ValueError, match="record_id=missing not in metadata"):
        load_record("missing", load_metadata(tmp_path), tmp_path)
