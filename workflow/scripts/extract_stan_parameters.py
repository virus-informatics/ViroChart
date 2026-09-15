#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def fields(line: str):
    start = 0
    while True:
        end = line.find(",", start)
        if end < 0:
            yield line[start:].rstrip("\r\n")
            return
        yield line[start:end]
        start = end + 1


def first_header_and_row(csv_path: Path) -> tuple[str, str]:
    with csv_path.open("r", encoding="utf-8") as handle:
        header = None
        for line in handle:
            if line.startswith("#"):
                continue
            if header is None:
                header = line
            else:
                return header, line
    raise ValueError(f"No data row found in Stan CSV: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    csv_group = parser.add_mutually_exclusive_group(required=True)
    csv_group.add_argument("--stan-csv", type=Path)
    csv_group.add_argument("--stan-csv-pointer", type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=("training", "embedding"), default="training")
    args = parser.parse_args()

    stan_csv = args.stan_csv
    if args.stan_csv_pointer is not None:
        stan_csv = Path(args.stan_csv_pointer.read_text(encoding="utf-8").strip())
    if stan_csv is None or not stan_csv.is_file():
        raise FileNotFoundError(f"Stan CSV not found: {stan_csv}")

    with (args.data_dir / "meta.json").open(encoding="utf-8") as handle:
        meta = json.load(handle)
    features = pd.read_csv(args.data_dir / "feature_order.csv")["feature"].astype(str).tolist()
    runs = pd.read_csv(args.data_dir / "metadata.csv")["Run"].astype(str).tolist()
    D, K, N = int(meta["D"]), int(meta["K"]), int(meta["N"])
    W = np.zeros((D, K))
    psi = np.zeros(D)
    z = np.zeros((N, K))
    found_w = found_psi = found_z = 0

    header_line, value_line = first_header_and_row(stan_csv)
    for name, raw_value in zip(fields(header_line), fields(value_line)):
        if name.startswith("W."):
            _, i, j = name.split(".")
            W[int(i) - 1, int(j) - 1] = float(raw_value)
            found_w += 1
        elif name.startswith("psi."):
            _, i = name.split(".")
            psi[int(i) - 1] = float(raw_value)
            found_psi += 1
        elif name.startswith("z_out."):
            _, i, j = name.split(".")
            z[int(i) - 1, int(j) - 1] = float(raw_value)
            found_z += 1

    expected = {"z_out": N * K}
    actual = {"z_out": found_z}
    if args.mode == "training":
        expected.update({"W": D * K, "psi": D})
        actual.update({"W": found_w, "psi": found_psi})
    if actual != expected:
        raise ValueError(f"Incomplete Stan parameters: expected={expected}, actual={actual}")

    factor_names = [f"factor_{i + 1}" for i in range(K)]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "training":
        pd.DataFrame(W, index=features, columns=factor_names).to_csv(
            args.output_dir / "W.csv", index=True, index_label="feature"
        )
        pd.DataFrame({"feature": features, "psi": psi}).to_csv(
            args.output_dir / "psi_prior.csv", index=False
        )
    pd.DataFrame(z, index=runs, columns=factor_names).to_csv(
        args.output_dir / "z_out.csv", index=True, index_label="Run"
    )
    (args.output_dir / ".parameters_extracted").touch()
    print(f"Extracted mode={args.mode}, W={W.shape}, psi={psi.shape}, z={z.shape}")



if __name__ == "__main__":
    main()
