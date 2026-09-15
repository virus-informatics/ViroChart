#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment


def metrics(reference: np.ndarray, candidate: np.ndarray) -> dict:
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

    old_w = pd.read_csv(args.reference_dir / "W.csv").to_numpy(dtype=float)
    new_w_frame = pd.read_csv(args.candidate_dir / "W.csv", index_col=0)
    new_w = new_w_frame.to_numpy(dtype=float)
    if old_w.shape != new_w.shape:
        raise ValueError(f"W shape mismatch: reference={old_w.shape}, candidate={new_w.shape}")

    correlation = np.corrcoef(old_w.T, new_w.T)[: old_w.shape[1], old_w.shape[1] :]
    old_index, new_index = linear_sum_assignment(-correlation)
    reordered_w = new_w[:, new_index]
    direct = metrics(old_w, new_w)
    matched = metrics(old_w[:, old_index], reordered_w)
    matched["reference_factor_order"] = old_index.tolist()
    matched["candidate_factor_order"] = new_index.tolist()
    matched["factor_correlations"] = correlation[old_index, new_index].tolist()

    old_psi = pd.read_csv(args.reference_dir / "psi_prior.csv").iloc[:, -1].to_numpy(dtype=float)
    new_psi = pd.read_csv(args.candidate_dir / "psi_prior.csv")["psi"].to_numpy(dtype=float)
    old_z = pd.read_csv(args.reference_dir / "z_out.csv", index_col=0).to_numpy(dtype=float)
    new_z = pd.read_csv(args.candidate_dir / "z_out.csv", index_col=0).to_numpy(dtype=float)

    report = {
        "W_direct": direct,
        "W_after_factor_matching": matched,
        "psi": metrics(old_psi, new_psi),
        "z_after_factor_matching": metrics(old_z[:, old_index], new_z[:, new_index]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

