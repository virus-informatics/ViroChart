#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

import argparse
import json
import re
from pathlib import Path


GENE_ID_RE = re.compile(r'(?:^|;\s*)gene_id "([^"]+)"')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    comments = 0
    exon_rows = 0
    kept_exons = 0
    missing_gene_id = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.input.open() as source, args.output.open("w") as destination:
        for line in source:
            if line.startswith("#"):
                destination.write(line)
                comments += 1
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "exon":
                continue
            exon_rows += 1
            match = GENE_ID_RE.search(fields[8])
            if not match or not match.group(1).strip():
                missing_gene_id += 1
                continue
            destination.write(line)
            kept_exons += 1

    report = {
        "source": str(args.input),
        "comment_rows": comments,
        "exon_rows": exon_rows,
        "kept_exons": kept_exons,
        "excluded_exons_missing_gene_id": missing_gene_id,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
