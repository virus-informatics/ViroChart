#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_feature_order(path: Path) -> tuple[list[str], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    features = [row["feature"].strip() for row in rows]
    pathways = [feature for feature in features if feature.startswith("map")]
    elements = [feature for feature in features if feature.startswith("N")]
    unsupported = [feature for feature in features if feature not in pathways and feature not in elements]
    if unsupported:
        raise ValueError(f"Unsupported trained features: {unsupported[:20]}")
    if len(features) != len(set(features)):
        raise ValueError("feature_order.csv contains duplicated feature names")
    return pathways, elements


def build_pathway_lines(pathway_ids: list[str], source: Path) -> list[str]:
    # ssGSEA normalization depends on the complete gene-set collection. Keep
    # the paper-time pathway GMT intact, including pathways not consumed by
    # Mode A, and only verify that every trained feature is available.
    lines = [line for line in source.read_text(encoding="utf-8-sig").splitlines() if line]
    source_ids = [line.split("\t", 1)[0] for line in lines]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError(f"Duplicated pathway IDs in {source}")
    missing = [pathway_id for pathway_id in pathway_ids if pathway_id not in source_ids]
    if missing:
        raise ValueError(f"Pathway GMT is missing trained features: {missing[:20]}")
    return lines


def build_element_lines(element_ids: list[str], source: Path) -> list[str]:
    indexed: dict[str, str] = {}
    with source.open(encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            element_id = line.split("\t", 1)[0]
            if element_id in indexed:
                raise ValueError(f"Duplicated element ID in {source}: {element_id}")
            indexed[element_id] = line
    missing = [element_id for element_id in element_ids if element_id not in indexed]
    if missing:
        raise ValueError(f"Element source is missing trained features: {missing[:20]}")
    return [indexed[element_id] for element_id in element_ids]


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines) + "\n"
    if not path.is_file() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def manifest_path(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build model-compatible final distribution GMT files from staged KEGG sources."
    )
    parser.add_argument("--species", required=True)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--feature-order", required=True, type=Path)
    parser.add_argument("--pathway-source-gmt", required=True, type=Path)
    parser.add_argument("--element-source", required=True, type=Path)
    parser.add_argument("--pathway-output", required=True, type=Path)
    parser.add_argument("--element-output", required=True, type=Path)
    parser.add_argument("--manifest-output", required=True, type=Path)
    args = parser.parse_args()

    pathway_ids, element_ids = read_feature_order(args.feature_order)
    pathway_lines = build_pathway_lines(pathway_ids, args.pathway_source_gmt)
    element_lines = build_element_lines(element_ids, args.element_source)
    write_lines(args.pathway_output, pathway_lines)
    write_lines(args.element_output, element_lines)

    manifest = {
        "status": "final_distribution_files",
        "species_id": args.species,
        "pathway_selection_policy": "preserve_complete_paper_snapshot_for_ssgsea_context",
        "element_selection_policy": "trained_model_feature_order",
        "pathway_feature_count": len(pathway_lines),
        "trained_pathway_feature_count": len(pathway_ids),
        "element_feature_count": len(element_ids),
        "outputs": {
            args.pathway_output.name: sha256_file(args.pathway_output),
            args.element_output.name: sha256_file(args.element_output),
        },
        "sources": {
            "feature_order": manifest_path(args.feature_order, args.project_root),
            "feature_order_sha256": sha256_file(args.feature_order),
            "pathway_source_gmt": manifest_path(args.pathway_source_gmt, args.project_root),
            "pathway_source_gmt_sha256": sha256_file(args.pathway_source_gmt),
            "element_source": manifest_path(args.element_source, args.project_root),
            "element_source_sha256": sha256_file(args.element_source),
        },
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
