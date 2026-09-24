#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito

set -euo pipefail

sample="$1"
read1="$2"
read2="$3"
index_prefix="$4"
result_dir="$5"
threads="$6"
sort_threads="$7"
sort_memory="$8"

mkdir -p "${result_dir}/qc" "${result_dir}/tmp"
trimmed1="${result_dir}/tmp/${sample}_1.fastp.fq.gz"
trimmed2="${result_dir}/tmp/${sample}_2.fastp.fq.gz"
bam="${result_dir}/${sample}.sorted.bam"

for required in "$read1" "$read2"; do
    if [[ ! -s "$required" ]]; then
        echo "[ERROR] Missing or empty input: $required" >&2
        exit 1
    fi
done

echo "[1/3] fastp: ${sample}"
fastp -i "$read1" -I "$read2" -o "$trimmed1" -O "$trimmed2" \
    -y -3 -x --thread "$threads" \
    --json "${result_dir}/qc/${sample}.fastp.json" \
    --html "${result_dir}/qc/${sample}.fastp.html"

echo "[2/3] HISAT2 + samtools sort: ${sample}"
hisat2 -p "$threads" -x "$index_prefix" -1 "$trimmed1" -2 "$trimmed2" \
    --summary-file "${result_dir}/qc/${sample}.hisat2.summary.txt" \
    2> "${result_dir}/qc/${sample}.hisat2.log" \
    | samtools sort -@ "$sort_threads" -m "$sort_memory" \
        -T "${result_dir}/tmp/${sample}.sort" -o "$bam" -
samtools index -@ "$sort_threads" "$bam"

{
    fastp --version 2>&1
    hisat2 --version 2>&1 | head -n 1
    samtools --version 2>&1 | head -n 1
} > "${result_dir}/software_versions.txt"

echo "[OK] Mapping completed: ${sample}"
