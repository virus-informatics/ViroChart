#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 7) {
  stop("Usage: ssgsea_single_sample.R TPM pathway.gmt element.gmt sample score.csv score_add.csv session.txt")
}

suppressPackageStartupMessages({
  library(GSVA)
  library(GSEABase)
})

tpm <- read.delim(args[1], row.names = 1, check.names = FALSE)
expression_matrix <- as.matrix(tpm)
storage.mode(expression_matrix) <- "double"

run_ssgsea <- function(gmt_path) {
  gene_sets <- getGmt(gmt_path)
  params <- ssgseaParam(expression_matrix, gene_sets, minSize = 2)
  gsva(params, verbose = FALSE)
}

write_score <- function(scores, sample_id, output_path) {
  score_row <- as.data.frame(t(scores), check.names = FALSE)
  rownames(score_row) <- sample_id
  score_row <- cbind(Run = rownames(score_row), score_row)
  write.csv(score_row, output_path, row.names = FALSE, quote = FALSE)
}

write_score(run_ssgsea(args[2]), args[4], args[5])
write_score(run_ssgsea(args[3]), args[4], args[6])
writeLines(capture.output(sessionInfo()), args[7])

