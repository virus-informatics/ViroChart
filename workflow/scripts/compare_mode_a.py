#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def matrix_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict:
    delta = candidate - reference
    return {
        "shape": list(reference.shape),
        "max_abs_error": float(np.max(np.abs(delta))),
        "mean_abs_error": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta**2))),
        "allclose_rtol_1e-6_atol_1e-8": bool(np.allclose(reference, candidate, rtol=1e-6, atol=1e-8)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", required=True, type=Path)
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    old_y = pd.read_csv(args.reference_dir / "Y.csv").to_numpy(dtype=float)
    new_y = pd.read_csv(args.candidate_dir / "Y.csv").to_numpy(dtype=float)
    old_z_frame = pd.read_csv(args.reference_dir / "z_out.csv", index_col=0)
    new_z_frame = pd.read_csv(args.candidate_dir / "z_out.csv", index_col=0)
    if old_y.shape != new_y.shape:
        raise ValueError(f"Y shape mismatch: {old_y.shape} vs {new_y.shape}")
    if old_z_frame.shape != new_z_frame.shape:
        raise ValueError(f"z shape mismatch: {old_z_frame.shape} vs {new_z_frame.shape}")
    if old_z_frame.index.astype(str).tolist() != new_z_frame.index.astype(str).tolist():
        raise ValueError("Run order differs between reference and candidate z_out.csv")

    report = {
        "Y": matrix_metrics(old_y, new_y),
        "z": matrix_metrics(old_z_frame.to_numpy(float), new_z_frame.to_numpy(float)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

