#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def select_sample(path: Path, sample_id: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "Run" not in frame.columns:
        raise ValueError(f"Run column is missing from {path}")
    selected = frame.loc[frame["Run"].astype(str) == sample_id].copy()
    if len(selected) != 1:
        raise ValueError(f"Expected one {sample_id} row in {path}, found {len(selected)}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble one FASTQ-derived Mode A input directory.")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--score", required=True, type=Path)
    parser.add_argument("--score-add", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    score = select_sample(args.score, args.sample_id)
    score_add = select_sample(args.score_add, args.sample_id)
    metadata = select_sample(args.metadata, args.sample_id)
    required_metadata = ["Run", "Genus", "genus", "BioProject"]
    missing = [column for column in required_metadata if column not in metadata.columns]
    if missing:
        raise ValueError(f"Metadata is missing required columns: {missing}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    score.to_csv(args.output_dir / "score.csv", index=False)
    score_add.to_csv(args.output_dir / "score_add.csv", index=False)
    metadata.loc[:, required_metadata].to_csv(args.output_dir / "metadata.csv", index=False)


if __name__ == "__main__":
    main()
