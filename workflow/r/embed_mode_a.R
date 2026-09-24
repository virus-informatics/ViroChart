#!/usr/bin/env Rscript
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito


suppressPackageStartupMessages({
  library(cmdstanr)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 11) {
  stop("Usage: embed_mode_a.R MODEL EXE DATA_DIR RESULT_DIR TRAINED_DIR K ITER SEED INIT CMDSTAN_PATH SESSION_LABEL")
}

model_file <- normalizePath(args[1])
exe_file <- normalizePath(args[2])
data_dir <- normalizePath(args[3])
result_dir <- args[4]
trained_dir <- normalizePath(args[5])
K <- as.integer(args[6])
iterations <- as.integer(args[7])
seed <- as.integer(args[8])
init <- as.numeric(args[9])
cmdstan_path_arg <- args[10]
session_label <- args[11]

if (nzchar(cmdstan_path_arg)) {
  set_cmdstan_path(cmdstan_path_arg)
}
dir.create(result_dir, recursive = TRUE, showWarnings = FALSE)
result_dir <- normalizePath(result_dir)

meta <- fromJSON(file.path(data_dir, "meta.json"))
Y <- as.matrix(read.csv(file.path(data_dir, "Y.csv"), check.names = FALSE))
W <- as.matrix(read.csv(file.path(trained_dir, "W.csv"), row.names = 1, check.names = FALSE))
psi_table <- read.csv(file.path(trained_dir, "psi_prior.csv"), check.names = FALSE)
psi_prior <- as.numeric(psi_table$psi)
stopifnot(nrow(Y) == meta$N, ncol(Y) == meta$D)
stopifnot(nrow(W) == meta$D, ncol(W) == K)
stopifnot(length(psi_prior) == meta$D)

dat <- list(N = meta$N, D = meta$D, K = K, Y = Y, W = W, psi_prior = psi_prior)
mod <- cmdstan_model(stan_file = model_file, exe_file = exe_file, compile = FALSE)
fit <- mod$optimize(
  data = dat,
  iter = iterations,
  algorithm = "lbfgs",
  output_dir = result_dir,
  save_latent_dynamics = TRUE,
  init = init,
  seed = seed,
  tol_grad = 1e2,
  tol_rel_obj = 1e-6,
  tol_rel_grad = 1e-4
)
csv_file <- fit$output_files()[1]
writeLines(csv_file, file.path(result_dir, "output_csv_path.txt"))
writeLines(capture.output(sessionInfo()), file.path(result_dir, paste0("r_session_info_", session_label, ".txt")))
writeLines(as.character(cmdstan_version()), file.path(result_dir, "cmdstan_version.txt"))
message("Mode A optimization finished: ", csv_file)

