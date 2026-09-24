#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_row(path, sample_id):
    table = pd.read_csv(path)
    id_column = "Run" if "Run" in table.columns else table.columns[0]
    rows = table.loc[table[id_column].astype(str) == sample_id]
    if len(rows) != 1:
        raise ValueError(f"expected exactly one {sample_id} row in {path}, found {len(rows)}")
    return pd.to_numeric(rows.iloc[0].drop(labels=[id_column]), errors="coerce")


def compare(candidate_path, reference_path, sample_id):
    candidate = load_row(candidate_path, sample_id).dropna()
    reference = load_row(reference_path, sample_id).dropna()
    common = candidate.index.intersection(reference.index)
    left = candidate.loc[common].astype(float).to_numpy()
    right = reference.loc[common].astype(float).to_numpy()
    delta = left - right
    return {
        "candidate_features": int(candidate.size),
        "reference_features": int(reference.size),
        "common_features": int(len(common)),
        "pearson_correlation": float(np.corrcoef(left, right)[0, 1]) if len(common) > 1 else None,
        "mean_absolute_error": float(np.mean(np.abs(delta))) if len(common) else None,
        "max_absolute_error": float(np.max(np.abs(delta))) if len(common) else None,
        "candidate_only": sorted(candidate.index.difference(reference.index).tolist()),
        "reference_only": sorted(reference.index.difference(candidate.index).tolist()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--candidate-score", type=Path, required=True)
    parser.add_argument("--candidate-score-add", type=Path, required=True)
    parser.add_argument("--reference-score", type=Path, required=True)
    parser.add_argument("--reference-score-add", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = {
        "sample_id": args.sample_id,
        "pathway": compare(args.candidate_score, args.reference_score, args.sample_id),
        "element": compare(args.candidate_score_add, args.reference_score_add, args.sample_id),
        "note": "Differences can reflect FASTQ source, reference assembly/annotation, tool versions, or preprocessing.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()

