from pathlib import Path

configfile: "../config/fastq_test.yaml"

ROOT = Path(workflow.basedir).parent.resolve()
SCRIPTS = ROOT / "workflow" / "scripts"
R_DIR = ROOT / "workflow" / "r"


def rooted(value):
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


SAMPLE = config["sample"]["id"]
SPECIES = config["sample"]["species_id"]
READ1 = rooted(config["sample"]["read1"])
READ2 = rooted(config["sample"]["read2"])
RESOURCE = rooted(config["paths"]["resource_dir"])
RESULT = rooted(config["paths"]["result_dir"])
VALIDATION = rooted(config["paths"]["validation_dir"])
FEATURE_ORDER_SOURCE = rooted(config["gene_sets"]["feature_order"])
PATHWAY_SOURCE_GMT = rooted(config["gene_sets"]["pathway_source_gmt"])
ELEMENT_SOURCE = rooted(config["gene_sets"]["element_source"])
DISTRIBUTION_GMT = rooted(config["gene_sets"]["distribution_dir"])
PAPER_SCORE = rooted(config["validation"]["paper_score"])
PAPER_SCORE_ADD = rooted(config["validation"]["paper_score_add"])
MODE_A_METADATA = rooted(config["mode_a"]["metadata"])
MODE_A_INPUT = rooted(config["mode_a"]["input_dir"])
PYTHON = config["execution"].get("python_path", "python3")
RSCRIPT = config["execution"].get("rscript_path", "Rscript")
TOOL_DIR = Path(config["execution"].get("tool_dir", Path(PYTHON).parent))
DATASETS = TOOL_DIR / "datasets"
HISAT2_BUILD = TOOL_DIR / "hisat2-build"
THREADS = int(config["execution"].get("threads", 8))
SORT_THREADS = int(config["execution"].get("samtools_sort_threads", 4))
SORT_MEMORY = config["execution"].get("samtools_sort_memory", "1G")

INDEX_FILES = [RESOURCE / f"{SPECIES}_index.{i}.ht2" for i in range(1, 9)]


rule all:
    input:
        VALIDATION / "fastq_gsva_comparison.json",


rule fastq_gsva:
    input:
        VALIDATION / "fastq_gsva_comparison.json",


rule mode_a_input:
    input:
        MODE_A_INPUT / "score.csv",
        MODE_A_INPUT / "score_add.csv",
        MODE_A_INPUT / "metadata.csv",


rule build_distribution_gene_sets:
    input:
        features=FEATURE_ORDER_SOURCE,
        pathway=PATHWAY_SOURCE_GMT,
        element=ELEMENT_SOURCE,
    output:
        pathway=DISTRIBUTION_GMT / f"pathway_{SPECIES}.gmt",
        element=DISTRIBUTION_GMT / f"element_{SPECIES}.gmt",
        manifest=DISTRIBUTION_GMT / "manifest.json",
    shell:
        "{PYTHON:q} {SCRIPTS}/build_distribution_gmt.py --species {SPECIES:q} --project-root {ROOT:q} "
        "--feature-order {input.features:q} --pathway-source-gmt {input.pathway:q} "
        "--element-source {input.element:q} "
        "--pathway-output {output.pathway:q} --element-output {output.element:q} "
        "--manifest-output {output.manifest:q}"


rule copy_gene_sets:
    input:
        pathway=rules.build_distribution_gene_sets.output.pathway,
        element=rules.build_distribution_gene_sets.output.element,
    output:
        pathway=RESOURCE / f"pathway_{SPECIES}.gmt",
        element=RESOURCE / f"element_{SPECIES}.gmt",
    shell:
        "mkdir -p {RESOURCE:q} && cp {input.pathway:q} {output.pathway:q} && cp {input.element:q} {output.element:q}"


rule prepare_reference:
    output:
        genome=RESOURCE / f"{SPECIES}.fna",
        gtf=RESOURCE / f"{SPECIES}.gtf",
        manifest=RESOURCE / "reference_manifest.json",
    params:
        accession=config["reference"]["accession"],
        taxon=config["reference"]["taxon_id"],
        output_dir=RESOURCE,
        datasets=DATASETS,
    shell:
        "{PYTHON:q} {SCRIPTS}/prepare_ncbi_reference.py "
        "--accession {params.accession:q} --taxon-id {params.taxon:q} "
        "--species-id {SPECIES:q} --output-dir {params.output_dir:q} "
        "--datasets-command {params.datasets:q}"


rule build_hisat2_index:
    input:
        genome=rules.prepare_reference.output.genome,
    output:
        INDEX_FILES,
    params:
        prefix=RESOURCE / f"{SPECIES}_index",
    threads: THREADS
    log:
        RESULT / "logs" / "hisat2_build.log",
    shell:
        "mkdir -p {RESULT}/logs && PATH={TOOL_DIR:q}:$PATH {HISAT2_BUILD:q} -p {threads} "
        "{input.genome:q} {params.prefix:q} > {log:q} 2>&1"


rule prepare_featurecounts_gtf:
    input:
        gtf=rules.prepare_reference.output.gtf,
    output:
        gtf=RESOURCE / f"{SPECIES}.featurecounts.gtf",
        report=RESOURCE / "featurecounts_gtf_report.json",
    shell:
        "{PYTHON:q} {SCRIPTS}/sanitize_gtf.py --input {input.gtf:q} --output {output.gtf:q} "
        "--report {output.report:q}"


rule map_fastq:
    input:
        read1=READ1,
        read2=READ2,
        index=rules.build_hisat2_index.output,
    output:
        bam=RESULT / f"{SAMPLE}.sorted.bam",
        bai=RESULT / f"{SAMPLE}.sorted.bam.bai",
        fastp_json=RESULT / "qc" / f"{SAMPLE}.fastp.json",
        fastp_html=RESULT / "qc" / f"{SAMPLE}.fastp.html",
        versions=RESULT / "software_versions.txt",
    params:
        sample=SAMPLE,
        index_prefix=RESOURCE / f"{SPECIES}_index",
        result_dir=RESULT,
        sort_threads=SORT_THREADS,
        sort_memory=SORT_MEMORY,
        tool_dir=TOOL_DIR,
    threads: THREADS
    log:
        RESULT / "logs" / "mapping.log",
    shell:
        "mkdir -p {RESULT}/logs && PATH={params.tool_dir:q}:$PATH bash {SCRIPTS}/map_local_fastq.sh {params.sample:q} {input.read1:q} {input.read2:q} "
        "{params.index_prefix:q} {params.result_dir:q} {threads} "
        "{params.sort_threads} {params.sort_memory:q} > {log:q} 2>&1"


rule feature_counts:
    input:
        bam=rules.map_fastq.output.bam,
        gtf=rules.prepare_featurecounts_gtf.output.gtf,
    output:
        counts=RESULT / f"{SAMPLE}_counts.tsv",
        summary=RESULT / f"{SAMPLE}_counts.tsv.summary",
    threads: THREADS
    log:
        RESULT / "logs" / "featurecounts.log",
    shell:
        "PATH={TOOL_DIR:q}:$PATH featureCounts -T {threads} -p -a {input.gtf:q} "
        "-o {output.counts:q} {input.bam:q} -t exon > {log:q} 2>&1"


rule counts_to_tpm:
    input:
        counts=rules.feature_counts.output.counts,
        gtf=rules.prepare_reference.output.gtf,
    output:
        tpm=RESULT / f"{SAMPLE}_TPM.txt",
        mapping=RESULT / f"{SAMPLE}_gene_id_mapping.json",
    shell:
        "{PYTHON:q} {SCRIPTS}/counts_to_tpm.py --counts {input.counts:q} --gtf {input.gtf:q} "
        "--output {output.tpm:q} --mapping-report {output.mapping:q}"


rule gsva_scores:
    input:
        tpm=rules.counts_to_tpm.output.tpm,
        pathway=rules.copy_gene_sets.output.pathway,
        element=rules.copy_gene_sets.output.element,
    output:
        pathway=RESULT / "score.csv",
        element=RESULT / "score_add.csv",
        session=RESULT / "r_session_info.txt",
    log:
        RESULT / "logs" / "gsva.log",
    shell:
        "mkdir -p {RESULT}/logs && {RSCRIPT:q} {R_DIR}/ssgsea_single_sample.R "
        "{input.tpm:q} {input.pathway:q} {input.element:q} {SAMPLE:q} "
        "{output.pathway:q} {output.element:q} {output.session:q} > {log:q} 2>&1"


rule compare_fastq_gsva:
    input:
        pathway=rules.gsva_scores.output.pathway,
        element=rules.gsva_scores.output.element,
        paper_pathway=PAPER_SCORE,
        paper_element=PAPER_SCORE_ADD,
        reference=rules.prepare_reference.output.manifest,
        mapping=rules.counts_to_tpm.output.mapping,
    output:
        VALIDATION / "fastq_gsva_comparison.json",
    shell:
        "{PYTHON:q} {SCRIPTS}/compare_gsva.py --sample-id {SAMPLE:q} "
        "--candidate-score {input.pathway:q} --candidate-score-add {input.element:q} "
        "--reference-score {input.paper_pathway:q} --reference-score-add {input.paper_element:q} "
        "--output {output:q}"


rule prepare_single_mode_a_input:
    input:
        score=rules.gsva_scores.output.pathway,
        score_add=rules.gsva_scores.output.element,
        metadata=MODE_A_METADATA,
    output:
        score=MODE_A_INPUT / "score.csv",
        score_add=MODE_A_INPUT / "score_add.csv",
        metadata=MODE_A_INPUT / "metadata.csv",
    params:
        output_dir=MODE_A_INPUT,
    shell:
        "{PYTHON:q} {SCRIPTS}/prepare_single_mode_a_input.py --sample-id {SAMPLE:q} "
        "--score {input.score:q} --score-add {input.score_add:q} --metadata {input.metadata:q} "
        "--output-dir {params.output_dir:q}"
