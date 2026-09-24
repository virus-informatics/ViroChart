# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_METADATA_COLUMNS = ("Run", "Genus", "genus", "BioProject")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_combo(input_dir: Path, fill_missing_with_zero: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    pathway_path = input_dir / "score.csv"
    entry_path = input_dir / "score_add.csv"
    metadata_path = input_dir / "metadata.csv"
    for path in (pathway_path, entry_path, metadata_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required input is missing: {path}")

    pathway = pd.read_csv(pathway_path)
    entry = pd.read_csv(entry_path)
    metadata = pd.read_csv(metadata_path)

    for label, frame in (("score.csv", pathway), ("score_add.csv", entry), ("metadata.csv", metadata)):
        if "Run" not in frame.columns:
            raise ValueError(f"{label} must contain a Run column")
        duplicates = frame["Run"].duplicated(keep=False)
        if duplicates.any():
            runs = frame.loc[duplicates, "Run"].astype(str).unique()[:10]
            raise ValueError(f"{label} contains duplicated Run values: {runs.tolist()}")

    missing_meta = [column for column in REQUIRED_METADATA_COLUMNS if column not in metadata.columns]
    if missing_meta:
        raise ValueError(f"metadata.csv is missing required columns: {missing_meta}")

    pathway = pathway.set_index("Run")
    entry = entry.set_index("Run")
    overlapping = pathway.columns.intersection(entry.columns)
    if len(overlapping):
        raise ValueError(f"Duplicated feature names across score files: {overlapping[:10].tolist()}")

    combo = pd.concat([pathway, entry], axis=1)
    if fill_missing_with_zero:
        combo = combo.fillna(0.0)
    elif combo.isna().any().any():
        raise ValueError("Combined score table contains missing values")

    merged = combo.reset_index().merge(metadata, on="Run", how="inner", validate="one_to_one", sort=False)
    missing_score_runs = sorted(set(combo.index.astype(str)) - set(merged["Run"].astype(str)))
    missing_metadata_runs = sorted(set(metadata["Run"].astype(str)) - set(merged["Run"].astype(str)))
    if missing_score_runs or missing_metadata_runs:
        raise ValueError(
            "Run mismatch between scores and metadata: "
            f"score_only={missing_score_runs[:10]}, metadata_only={missing_metadata_runs[:10]}"
        )

    feature_names = combo.columns.tolist()
    scores = merged.set_index("Run")[feature_names]
    metadata_aligned = merged[metadata.columns].copy()
    return scores, metadata_aligned


def apply_host_filter(
    scores: pd.DataFrame, metadata: pd.DataFrame, host_min_count: int | None
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    if host_min_count is None:
        return scores, metadata, []
    counts = metadata["Genus"].value_counts()
    removed_hosts = counts[counts < host_min_count].index.astype(str).tolist()
    keep = metadata["Genus"].isin(counts[counts >= host_min_count].index).to_numpy()
    filtered_metadata = metadata.loc[keep].reset_index(drop=True)
    filtered_scores = scores.loc[filtered_metadata["Run"]].copy()
    return filtered_scores, filtered_metadata, removed_hosts


def build_laplacian_from_jaccard(
    frame: pd.DataFrame, drop_nonzero_bottom_q: float = 0.10, eps_diag: float = 1e-6
) -> np.ndarray:
    if not frame.index.equals(frame.columns):
        frame = frame.loc[frame.index, frame.index]
    similarity = frame.to_numpy(dtype=float)
    np.fill_diagonal(similarity, 0.0)
    off_diagonal = similarity[~np.eye(similarity.shape[0], dtype=bool)]
    nonzero = off_diagonal[off_diagonal > 0]
    if nonzero.size and drop_nonzero_bottom_q > 0:
        threshold = np.quantile(nonzero, drop_nonzero_bottom_q)
        similarity = np.where(similarity >= threshold, similarity, 0.0)
    similarity = 0.5 * (similarity + similarity.T)
    degree = similarity.sum(axis=1)
    return np.diag(degree) - similarity + eps_diag * np.eye(similarity.shape[0])


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

