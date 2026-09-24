#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

import argparse
import json
import re
from pathlib import Path

import pandas as pd


ATTR_RE = re.compile(r'(\S+) "([^"]+)"')


def read_gtf_gene_map(path):
    mapping = {}
    with path.open() as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "gene":
                continue
            attrs = dict(ATTR_RE.findall(fields[8]))
            geneid_match = re.search(r'(?:^|,)GeneID:(\d+)(?:,|$)', attrs.get("db_xref", ""))
            if not geneid_match:
                continue
            gene_id = geneid_match.group(1)
            for key in ("gene_id", "gene", "gene_name"):
                value = attrs.get(key)
                if value:
                    mapping[value] = gene_id
                    mapping[value.removeprefix("gene-")] = gene_id
    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--gtf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mapping-report", type=Path, required=True)
    args = parser.parse_args()

    counts = pd.read_csv(args.counts, sep="\t", comment="#")
    required = {"Geneid", "Length"}
    if not required.issubset(counts.columns):
        raise ValueError(f"featureCounts columns missing: {sorted(required - set(counts.columns))}")
    sample_columns = list(counts.columns[6:])
    if len(sample_columns) != 1:
        raise ValueError(f"expected one count column, found {sample_columns}")

    gene_map = read_gtf_gene_map(args.gtf)
    original_ids = counts["Geneid"].astype(str)
    numeric = original_ids.where(original_ids.str.fullmatch(r"\d+"))
    mapped = original_ids.map(gene_map).fillna(numeric)
    counts = counts.assign(GeneID=mapped).dropna(subset=["GeneID"])

    values = pd.to_numeric(counts[sample_columns[0]], errors="coerce").fillna(0.0)
    lengths_kb = pd.to_numeric(counts["Length"], errors="coerce").fillna(0.0) / 1000.0
    rpk = values.where(lengths_kb > 0, 0.0) / lengths_kb.where(lengths_kb > 0, 1.0)
    counts = counts.assign(RPK=rpk)
    grouped = counts.groupby("GeneID", sort=False, as_index=False)["RPK"].sum()
    denominator = grouped["RPK"].sum()
    if denominator <= 0:
        raise ValueError("total RPK is zero")
    grouped["TPM"] = grouped["RPK"] / denominator * 1_000_000.0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    grouped[["GeneID", "TPM"]].to_csv(args.output, sep="\t", index=False, float_format="%.6f")
    report = {
        "featurecounts_rows": int(len(original_ids)),
        "mapped_rows": int(counts.shape[0]),
        "unmapped_rows": int(len(original_ids) - counts.shape[0]),
        "unique_gene_ids": int(grouped.shape[0]),
        "tpm_sum": float(grouped["TPM"].sum()),
    }
    args.mapping_report.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()

