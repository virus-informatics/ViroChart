#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.preprocessing import StandardScaler

from common import (
    apply_host_filter,
    build_laplacian_from_jaccard,
    load_combo,
    sha256_file,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the paper-compatible Mode B training data.")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--prior-matrix", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--k", required=True, type=int)
    parser.add_argument("--host-min-count", type=int)
    parser.add_argument("--no-fill-missing", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scores, metadata = load_combo(args.input_dir, not args.no_fill_missing)
    input_sample_count = len(scores)
    scores, metadata, removed_hosts = apply_host_filter(scores, metadata, args.host_min_count)

    prior = pd.read_csv(args.prior_matrix, sep="\t", index_col=0)
    missing_prior_features = [name for name in scores.columns if name not in prior.index]
    if missing_prior_features:
        raise ValueError(
            "Training features are missing from the Jaccard prior: "
            f"{missing_prior_features[:20]} (total={len(missing_prior_features)})"
        )
    # 論文コードと同じ順序: 全priorで枝刈り・Laplacian化してから学習特徴量へ絞る。
    full_laplacian = build_laplacian_from_jaccard(prior)
    full_laplacian = pd.DataFrame(full_laplacian, index=prior.index, columns=prior.columns)
    laplacian = full_laplacian.loc[scores.columns, scores.columns].to_numpy()

    scaler = StandardScaler().fit(scores.to_numpy(dtype=float))
    y_scaled = scaler.transform(scores.to_numpy(dtype=float))

    host_dummies = pd.get_dummies(metadata["Genus"], drop_first=False)
    virus_dummies = pd.get_dummies(metadata["genus"], drop_first=False)
    bioproject_dummies = pd.get_dummies(metadata["BioProject"], drop_first=False)
    host_id, host_labels = pd.factorize(metadata["Genus"])
    virus_id, virus_labels = pd.factorize(metadata["genus"])
    bioproject_id, bioproject_labels = pd.factorize(metadata["BioProject"])
    host_id += 1
    virus_id += 1
    bioproject_id += 1
    if len(virus_labels):
        virus_dummies.iloc[np.where(virus_id == 1)[0], :] = False

    scores.to_csv(args.output_dir / "score_combo.csv", index=True, index_label="Run")
    metadata.to_csv(args.output_dir / "metadata.csv", index=False)
    pd.DataFrame(y_scaled, index=scores.index, columns=scores.columns).to_csv(
        args.output_dir / "Y.csv", index=False
    )
    host_dummies.astype(int).to_csv(args.output_dir / "X_host.csv", index=False)
    virus_dummies.astype(int).to_csv(args.output_dir / "X_virus.csv", index=False)
    bioproject_dummies.astype(int).to_csv(args.output_dir / "X_bioproject.csv", index=False)
    pd.DataFrame(
        {"host_id": host_id, "virus_id": virus_id, "bioproject_id": bioproject_id}
    ).to_csv(args.output_dir / "ids.csv", index=False)
    pd.DataFrame(
        {"host_id": range(1, len(host_labels) + 1), "host_label": host_labels}
    ).to_csv(args.output_dir / "host_mapping.csv", index=False)
    pd.DataFrame(
        {"virus_id": range(1, len(virus_labels) + 1), "virus_label": virus_labels}
    ).to_csv(args.output_dir / "virus_mapping.csv", index=False)
    pd.DataFrame(
        {"bioproject_id": range(1, len(bioproject_labels) + 1), "bioproject_label": bioproject_labels}
    ).to_csv(args.output_dir / "bioproject_mapping.csv", index=False)
    pd.DataFrame(laplacian, index=scores.columns, columns=scores.columns).to_csv(
        args.output_dir / "L_w_prior.csv", index=True
    )
    pd.DataFrame({"feature": scores.columns, "position": range(len(scores.columns))}).to_csv(
        args.output_dir / "feature_order.csv", index=False
    )
    joblib.dump(scaler, args.output_dir / "scaler.joblib")

    meta = {
        "N": len(scores),
        "D": scores.shape[1],
        "K": args.k,
        "P_host": host_dummies.shape[1],
        "P_virus": virus_dummies.shape[1],
        "P_bioproject": bioproject_dummies.shape[1],
    }
    write_json(args.output_dir / "meta.json", meta)
    manifest = {
        "mode": "B",
        "input_sample_count": input_sample_count,
        "training_sample_count": len(scores),
        "feature_count": scores.shape[1],
        "host_min_count": args.host_min_count,
        "removed_hosts": removed_hosts,
        "fill_combo_missing_with_zero": not args.no_fill_missing,
        "feature_alignment": "strict_paper_order",
        "input_sha256": {
            name: sha256_file(args.input_dir / name)
            for name in ("score.csv", "score_add.csv", "metadata.csv")
        },
        "prior_sha256": sha256_file(args.prior_matrix),
        "python": sys.version,
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
    }
    write_json(args.output_dir / "preprocessing_manifest.json", manifest)
    (args.output_dir / ".mode_b_prepared").touch()
    print(f"Prepared Mode B data: N={len(scores)}, D={scores.shape[1]}, K={args.k}")
    print(f"Removed hosts: {removed_hosts}")


if __name__ == "__main__":
    main()
