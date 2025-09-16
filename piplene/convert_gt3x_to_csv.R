#!/usr/bin/env Rscript

# ============================
# Auto-convert .gt3x -> .csv
# Looks for .gt3x files in ../data (relative to pipeline/) or ./data
# Converts only new/updated files and saves .csv into the same data/ folder
# ============================

suppressPackageStartupMessages({
  # Prefer user-level library (portable across machines/CI)
  rlib <- Sys.getenv("R_LIBS_USER")
  if (!nzchar(rlib)) {
    # Reasonable fallback if the env var isn't set
    rlib <- file.path(path.expand("~"), "R", "library")
  }
  if (!dir.exists(rlib)) dir.create(rlib, recursive = TRUE, showWarnings = FALSE)
  .libPaths(c(rlib, .libPaths()))
})

# Ensure remotes is available
if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes", lib = .libPaths()[1L])
}

# Ensure read.gt3x is available
if (!requireNamespace("read.gt3x", quietly = TRUE)) {
  remotes::install_github("THLfi/read.gt3x", upgrade = "never", lib = .libPaths()[1L])
}

suppressPackageStartupMessages({
  library(read.gt3x)
})

# --------- Helpers: script path & data dir ----------
get_script_path <- function() {
  # 1) When run via Rscript --file
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) == 1) return(normalizePath(sub("^--file=", "", file_arg)))
  # 2) When sourced in R (may not always work)
  if (!is.null(sys.frames()) && !is.null(sys.frames()[[1]]$ofile)) {
    return(normalizePath(sys.frames()[[1]]$ofile))
  }
  # 3) Fallback: working directory
  return(normalizePath(file.path(getwd(), "convert_gt3x_to_csv.R"), mustWork = FALSE))
}

script_path <- get_script_path()
script_dir  <- dirname(script_path)

# Allow override via env var (e.g., DATA_DIR=/path/to/data Rscript pipeline/convert_gt3x_to_csv.R)
data_dir_env <- Sys.getenv("DATA_DIR")
if (nzchar(data_dir_env) && dir.exists(data_dir_env)) {
  data_dir <- normalizePath(data_dir_env)
} else {
  # Typical repo layout: pipeline/ -> ../data
  candidate1 <- normalizePath(file.path(script_dir, "..", "data"), mustWork = FALSE)
  candidate2 <- normalizePath(file.path(script_dir, "data"), mustWork = FALSE)
  if (dir.exists(candidate1)) {
    data_dir <- candidate1
  } else if (dir.exists(candidate2)) {
    data_dir <- candidate2
  } else {
    stop("❌ 'data' folder not found in '../data' or './data'. Set DATA_DIR env var or create the folder.")
  }
}

cat(sprintf("📂 Data folder: %s\n", data_dir))

# --------- Find GT3X files ----------
gt3x_files <- list.files(data_dir, pattern = "\\.gt3x$", full.names = TRUE, ignore.case = TRUE)
if (length(gt3x_files) == 0) {
  cat("ℹ️ No .gt3x files found. Nothing to do.\n")
  quit(status = 0)
}

# --------- Conversion function ----------
convert_one <- function(gt3x_path) {
  base <- tools::file_path_sans_ext(basename(gt3x_path))
  csv_path <- file.path(data_dir, paste0(base, ".csv"))

  # Convert only if CSV is missing or older than the GT3X
  need_convert <- !file.exists(csv_path)
  if (!need_convert) {
    m_gt3x <- file.info(gt3x_path)$mtime
    m_csv  <- file.info(csv_path)$mtime
    need_convert <- is.na(m_csv) || is.na(m_gt3x) || m_gt3x > m_csv
  }

  if (!need_convert) {
    cat(sprintf("⏭️  Up-to-date, skipping: %s\n", basename(csv_path)))
    return(invisible(FALSE))
  }

  cat(sprintf("🔄 Converting: %s -> %s\n", basename(gt3x_path), basename(csv_path)))

  tryCatch({
    df <- read.gt3x(gt3x_path, asDataFrame = TRUE)
    utils::write.csv(df, csv_path, row.names = FALSE)
    cat(sprintf("✅ Done: %s\n", basename(csv_path)))
    invisible(TRUE)
  }, error = function(e) {
    cat(sprintf("❌ Failed: %s\n   Reason: %s\n", basename(gt3x_path), conditionMessage(e)))
    invisible(FALSE)
  })
}

# --------- Run conversions ----------
results <- vapply(gt3x_files, convert_one, logical(1))
n_ok   <- sum(results, na.rm = TRUE)
n_skip <- sum(!results, na.rm = TRUE)

cat("\n==================== SUMMARY ====================\n")
cat(sprintf("Total .gt3x found     : %d\n", length(gt3x_files)))
cat(sprintf("Converted/updated     : %d\n", n_ok))
cat(sprintf("Skipped or failed     : %d\n", n_skip))
cat("=================================================\n")
