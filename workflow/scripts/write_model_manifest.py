#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import sha256_file, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--stan-model", required=True, type=Path)
    parser.add_argument("--stan-executable", required=True, type=Path)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    files = ("W.csv", "psi_prior.csv", "scaler.joblib", "feature_order.csv", "meta.json")
    with (args.model_dir / "meta.json").open(encoding="utf-8") as handle:
        meta = json.load(handle)
    manifest = {
        "model_dimensions": meta,
        "files_sha256": {name: sha256_file(args.model_dir / name) for name in files},
        "stan_model_sha256": sha256_file(args.stan_model),
        "stan_executable_sha256": sha256_file(args.stan_executable),
        "cmdstan_version": (args.result_dir / "cmdstan_version.txt").read_text().strip(),
        "r_session_info_file": str((args.result_dir / "r_session_info.txt").relative_to(args.model_dir)),
    }
    write_json(args.output, manifest)
    print(f"Wrote model manifest: {args.output}")


if __name__ == "__main__":
    main()
