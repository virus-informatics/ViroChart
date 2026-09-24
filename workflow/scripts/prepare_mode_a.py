#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

from common import load_combo, sha256_file, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Mode A with the scaler fitted by Mode B.")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--trained-model-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--k", required=True, type=int)
    args = parser.parse_args()

    required_model_files = (
        "W.csv",
        "psi_prior.csv",
        "scaler.joblib",
        "feature_order.csv",
        "meta.json",
        "preprocessing_manifest.json",
    )
    for name in required_model_files:
        path = args.trained_model_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Required trained-model file is missing: {path}")

    scores, metadata = load_combo(args.input_dir, fill_missing_with_zero=True)
    features = pd.read_csv(args.trained_model_dir / "feature_order.csv")["feature"].astype(str).tolist()
    missing = [feature for feature in features if feature not in scores.columns]
    extra = [feature for feature in scores.columns if feature not in features]
    if missing:
        raise ValueError(f"Embedding input is missing trained features: {missing[:20]} (total={len(missing)})")
    scores = scores.loc[:, features]

    W = pd.read_csv(args.trained_model_dir / "W.csv", index_col=0)
    psi = pd.read_csv(args.trained_model_dir / "psi_prior.csv")
    if W.index.astype(str).tolist() != features:
        raise ValueError("W.csv feature order does not match feature_order.csv")
    if psi["feature"].astype(str).tolist() != features:
        raise ValueError("psi_prior.csv feature order does not match feature_order.csv")
    if W.shape != (len(features), args.k):
        raise ValueError(f"W shape mismatch: expected={(len(features), args.k)}, actual={W.shape}")

    scaler = joblib.load(args.trained_model_dir / "scaler.joblib")
    if int(scaler.n_features_in_) != len(features):
        raise ValueError(
            f"Scaler feature count mismatch: expected={len(features)}, actual={scaler.n_features_in_}"
        )
    y_scaled = scaler.transform(scores.to_numpy(dtype=float))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scores.to_csv(args.output_dir / "score_combo.csv", index=True, index_label="Run")
    metadata.to_csv(args.output_dir / "metadata.csv", index=False)
    pd.DataFrame(y_scaled, index=scores.index, columns=features).to_csv(
        args.output_dir / "Y.csv", index=False
    )
    pd.DataFrame({"feature": features, "position": range(len(features))}).to_csv(
        args.output_dir / "feature_order.csv", index=False
    )
    write_json(args.output_dir / "meta.json", {"N": len(scores), "D": len(features), "K": args.k})
    write_json(
        args.output_dir / "embedding_manifest.json",
        {
            "mode": "A",
            "sample_count": len(scores),
            "feature_count": len(features),
            "extra_input_features_ignored": extra,
            "trained_model_id": args.trained_model_dir.name,
            "trained_model_sha256": {
                name: sha256_file(args.trained_model_dir / name) for name in required_model_files
            },
            "input_sha256": {
                name: sha256_file(args.input_dir / name)
                for name in ("score.csv", "score_add.csv", "metadata.csv")
            },
            "scaler_policy": "load_training_scaler_and_transform_without_refit",
        },
    )
    (args.output_dir / ".mode_a_prepared").touch()
    print(f"Prepared Mode A data: N={len(scores)}, D={len(features)}, K={args.k}")
    print(f"Ignored extra input features: {len(extra)}")


if __name__ == "__main__":
    main()
