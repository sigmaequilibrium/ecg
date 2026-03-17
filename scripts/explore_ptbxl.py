#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick PTB-XL exploratory summary")
    parser.add_argument("root", type=Path, help="Path to PTB-XL root folder")
    parser.add_argument("--beats-csv", type=str, default=None, help="Optional beat annotation CSV")
    args = parser.parse_args()

    from ecg_analysis.config import PTBXLConfig
    from ecg_analysis.data.ptbxl import PTBXLLoader

    config = PTBXLConfig(root=args.root, beats_csv=args.beats_csv)
    loader = PTBXLLoader(config)

    metadata = loader.load_metadata()
    print("Records:", len(metadata))
    print("By split:")
    print(metadata["split"].value_counts(dropna=False).sort_index())

    anns = loader.load_beat_annotations()
    print("Beat annotations:", len(anns))
    if anns:
        issues = loader.validate_annotations(anns)
        print("Validation issues:", len(issues))
        for issue in issues[:10]:
            print(issue)


if __name__ == "__main__":
    main()
