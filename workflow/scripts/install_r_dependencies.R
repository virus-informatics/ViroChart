#!/usr/bin/env Rscript
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: Copyright 2026 Junna Kawasaki & Jumpei Ito


options(repos = c(
  STAN = "https://stan-dev.r-universe.dev",
  CRAN = "https://cloud.r-project.org"
))

if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager")
}

bioconductor_packages <- c("GSVA", "GSEABase")
missing_bioconductor <- bioconductor_packages[
  !vapply(bioconductor_packages, requireNamespace, logical(1), quietly = TRUE)
]
if (length(missing_bioconductor) > 0) {
  BiocManager::install(missing_bioconductor, ask = FALSE, update = FALSE)
}

if (!requireNamespace("cmdstanr", quietly = TRUE)) {
  install.packages("cmdstanr")
}

required <- c("GSVA", "GSEABase", "cmdstanr", "jsonlite")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) {
  stop("Failed to install required R packages: ", paste(missing, collapse = ", "))
}

cat("R dependency check passed.\n")
cat("R:", R.version.string, "\n")
for (package in required) {
  cat(package, as.character(utils::packageVersion(package)), "\n")
}
cmdstan_version <- as.character(cmdstanr::cmdstan_version())
if (cmdstan_version != "2.36.0") {
  stop("CmdStan 2.36.0 is required, but cmdstanr detected ", cmdstan_version)
}
cat("CmdStan:", cmdstan_version, "\n")
