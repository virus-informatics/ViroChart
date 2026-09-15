#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def metrics(candidate: np.ndarray, reference: np.ndarray) -> dict:
    delta = candidate - reference
    return {
        "shape": list(candidate.shape),
        "pearson_correlation": float(np.corrcoef(candidate.ravel(), reference.ravel())[0, 1]),
        "mean_absolute_error": float(np.mean(np.abs(delta))),
        "max_absolute_error": float(np.max(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta**2))),
    }


def select_row(path: Path, sample_id: str) -> pd.Series:
    frame = pd.read_csv(path).set_index("Run")
    if sample_id not in frame.index:
        raise ValueError(f"{sample_id} is missing from {path}")
    return frame.loc[sample_id]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare FASTQ-derived Mode A Y/z with paper data.")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--trained-model-dir", required=True, type=Path)
    parser.add_argument("--paper-score", required=True, type=Path)
    parser.add_argument("--paper-score-add", required=True, type=Path)
    parser.add_argument("--paper-z", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    features = pd.read_csv(args.trained_model_dir / "feature_order.csv")["feature"].astype(str).tolist()
    paper_score = select_row(args.paper_score, args.sample_id)
    paper_element = select_row(args.paper_score_add, args.sample_id)
    paper_combo = pd.concat([paper_score, paper_element]).loc[features].to_numpy(float).reshape(1, -1)
    scaler = joblib.load(args.trained_model_dir / "scaler.joblib")
    paper_y = scaler.transform(paper_combo)
    candidate_y = pd.read_csv(args.candidate_dir / "Y.csv").to_numpy(float)

    candidate_z = select_row(args.candidate_dir / "z_out.csv", args.sample_id).to_numpy(float)
    paper_z = select_row(args.paper_z, args.sample_id).to_numpy(float)
    report = {
        "sample_id": args.sample_id,
        "comparison_basis": "paper GSVA scores transformed with the same training scaler; paper Mode A z",
        "Y": metrics(candidate_y, paper_y),
        "z": metrics(candidate_z, paper_z),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
