#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--accession", required=True)
    parser.add_argument("--taxon-id", required=True)
    parser.add_argument("--species-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--datasets-command", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    genome_out = args.output_dir / f"{args.species_id}.fna"
    gtf_out = args.output_dir / f"{args.species_id}.gtf"
    manifest_out = args.output_dir / "reference_manifest.json"

    with tempfile.TemporaryDirectory(prefix=f"{args.species_id}_ncbi_", dir=args.output_dir) as temp_name:
        temp = Path(temp_name)
        archive = temp / "reference.zip"
        subprocess.run(
            [str(args.datasets_command), "download", "genome", "accession", args.accession,
             "--include", "genome,gtf", "--filename", str(archive)],
            check=True,
        )
        with zipfile.ZipFile(archive) as bundle:
            bad_member = bundle.testzip()
            if bad_member:
                raise RuntimeError(f"corrupt NCBI archive member: {bad_member}")
            bundle.extractall(temp / "extracted")

        genomes = sorted((temp / "extracted").rglob("*_genomic.fna"))
        gtfs = sorted((temp / "extracted").rglob("*.gtf"))
        if len(genomes) != 1 or len(gtfs) != 1:
            raise RuntimeError(f"expected one genome and one GTF, found {len(genomes)} and {len(gtfs)}")
        shutil.copy2(genomes[0], genome_out)
        shutil.copy2(gtfs[0], gtf_out)

    manifest = {
        "species_id": args.species_id,
        "taxon_id": str(args.taxon_id),
        "ncbi_accession": args.accession,
        "genome": {"file": genome_out.name, "sha256": sha256(genome_out), "bytes": genome_out.stat().st_size},
        "gtf": {"file": gtf_out.name, "sha256": sha256(gtf_out), "bytes": gtf_out.stat().st_size},
    }
    manifest_out.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
