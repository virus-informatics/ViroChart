#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(cmdstanr)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 10) {
  stop("Usage: train_mode_b.R MODEL EXE DATA_DIR RESULT_DIR K ITER LAMBDA SEED INIT CMDSTAN_PATH")
}

model_file <- normalizePath(args[1])
exe_file <- normalizePath(args[2])
data_dir <- normalizePath(args[3])
result_dir <- args[4]
K <- as.integer(args[5])
iterations <- as.integer(args[6])
lambda_w <- as.numeric(args[7])
seed <- as.integer(args[8])
init <- as.numeric(args[9])
cmdstan_path_arg <- args[10]

if (nzchar(cmdstan_path_arg)) {
  set_cmdstan_path(cmdstan_path_arg)
}
dir.create(result_dir, recursive = TRUE, showWarnings = FALSE)
result_dir <- normalizePath(result_dir)

meta <- fromJSON(file.path(data_dir, "meta.json"))
Y <- as.matrix(read.csv(file.path(data_dir, "Y.csv"), check.names = FALSE))
L_w <- as.matrix(read.csv(file.path(data_dir, "L_w_prior.csv"), row.names = 1, check.names = FALSE))
stopifnot(nrow(Y) == meta$N, ncol(Y) == meta$D)
stopifnot(nrow(L_w) == meta$D, ncol(L_w) == meta$D)
stopifnot(max(abs(L_w - t(L_w))) < 1e-8)

dat <- list(N = meta$N, D = meta$D, K = K, Y = Y, L_w = L_w, lambda_w = lambda_w)
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
writeLines(capture.output(sessionInfo()), file.path(result_dir, "r_session_info.txt"))
writeLines(as.character(cmdstan_version()), file.path(result_dir, "cmdstan_version.txt"))
message("Mode B optimization finished: ", csv_file)
