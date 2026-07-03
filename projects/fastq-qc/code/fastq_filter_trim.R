library(ShortRead)
library(Biostrings)
library(knitr)

# Show only what is required in the PDF and save R Markdown figures as PNG
knitr::opts_chunk$set(
  fig.path = "figures/",
  dev = "png",
  dpi = 150,
  echo = FALSE,
  message = FALSE,
  warning = FALSE,
  purl = FALSE
)

if (!dir.exists("figures")) {
  dir.create("figures", recursive = TRUE)
}

# Plot settings
par(cex.axis = 0.8, cex.lab = 0.9, cex.main = 1.0)

cat("Give the name of .fastq file for analysis, e.g. ex02.fastq: ", file = stderr())

fastqname <- readLines("stdin", n = 1)
fastqname <- trimws(fastqname)

if (fastqname == "") {
  stop("Wrong FASTQ filename or file does not exist.")
}

if (!file.exists(fastqname)) {
  stop(paste("File not found:", fastqname))
}

step_plot <- 5

# Decision from the BEFORE plot:
k_trim <- 50     # trim 50 bases from the end, so the first 200 bases are kept

fastq_raw <- readFastq(fastqname)
seq_raw   <- sread(fastq_raw)
qual_raw  <- as(quality(fastq_raw), "matrix")

n_reads_raw <- length(fastq_raw)

# Readable quality boxplot
quality_boxplot <- function(qual_mat, main, step = 5) {
  idx <- seq(1, ncol(qual_mat), by = step)

  boxplot(
    qual_mat[, idx, drop = FALSE],
    xlab = "Base position",
    ylab = "Phred quality",
    main = main,
    range = 0,         # whiskers show the full quality range
    outline = FALSE,   # hide outliers to make the plot easier to read
    lwd = 0.3,
    lty = 1,
    xaxt = "n"
  )

  axis(1, at = seq_along(idx), labels = idx)
  grid(nx = NA, ny = NULL)
}

quality_boxplot(
  qual_raw,
  main = paste0(fastqname, " - BEFORE"),
  step = step_plot
)

# Save the BEFORE plot as a PNG file for the portfolio website
png("figures/fastq_before.png", width = 1200, height = 700, res = 150)

quality_boxplot(
  qual_raw,
  main = paste0(fastqname, " - BEFORE"),
  step = step_plot
)

invisible(dev.off())

# 1) Remove reads containing N
n_count <- letterFrequency(seq_raw, letters = "N")[, 1]
keep_noN <- (n_count == 0)
fastq_noN <- fastq_raw[keep_noN]

n_removed_N <- sum(!keep_noN)

# 2) Trim a fixed number of bases from the end
end_pos <- width(sread(fastq_noN)) - k_trim
keep_len <- end_pos >= 1

fastq_trim <- narrow(
  fastq_noN[keep_len],
  start = 1,
  end = end_pos[keep_len]
)

n_after_trim <- length(fastq_trim)
qual_after <- as(quality(fastq_trim), "matrix")

quality_boxplot(
  qual_after,
  main = paste0(fastqname, " - AFTER (no N, -", k_trim, " bases)"),
  step = step_plot
)

# Save the AFTER plot as a PNG file for the portfolio website
png("figures/fastq_after.png", width = 1200, height = 700, res = 150)

quality_boxplot(
  qual_after,
  main = paste0(fastqname, " - AFTER (no N, -", k_trim, " bases)"),
  step = step_plot
)

invisible(dev.off())

# #!/usr/bin/env Rscript
# 
# # Project 4 / Set 2: FASTQ filtering + fixed trimming + final quality plot
# 
# suppressPackageStartupMessages({
#   library(ShortRead)
#   library(Biostrings)
# })
# 
# input <- function(prompt) {
#   cat(prompt)
#   flush.console()
#   readLines("stdin", n = 1)
# }
# 
# args <- commandArgs(trailingOnly = TRUE)
# 
# # Input FASTQ name, from argument or interactive question
# if (length(args) >= 1 && nzchar(args[1])) {
#   fastqname <- args[1]
# } else {
#   fastqname <- input("Enter the name of a FASTQ file: ")
# }
# 
# if (!file.exists(fastqname)) {
#   stop("File not found: ", fastqname)
# }
# 
# # Trim length, fixed number of bases removed from the end
# trim_txt <- if (length(args) >= 2 && nzchar(args[2])) {
#   args[2]
# } else {
#   input("How many bases to trim from the end? (default 50): ")
# }
# 
# if (!nzchar(trim_txt)) trim_txt <- "50"
# 
# TRIM_END <- suppressWarnings(as.integer(trim_txt))
# 
# if (is.na(TRIM_END) || TRIM_END < 0) {
#   stop("Invalid TRIM_END: ", trim_txt)
# }
# 
# # Plot step, show every n-th base on the x-axis
# step_txt <- if (length(args) >= 3 && nzchar(args[3])) {
#   args[3]
# } else {
#   input("Plot every n-th base position? (default 5): ")
# }
# 
# if (!nzchar(step_txt)) step_txt <- "5"
# 
# STEP <- suppressWarnings(as.integer(step_txt))
# 
# if (is.na(STEP) || STEP < 1) {
#   stop("Invalid STEP: ", step_txt)
# }
# 
# # Output compression
# comp_txt <- if (length(args) >= 4 && nzchar(args[4])) {
#   args[4]
# } else {
#   input("Compress output FASTQ? [Y/n]: ")
# }
# 
# comp_txt <- tolower(trimws(comp_txt))
# compress_out <- !(comp_txt %in% c("n", "no", "0"))
# 
# # Read FASTQ
# fastq <- readFastq(fastqname)
# 
# # FILTER: remove reads containing at least one N
# seq <- sread(fastq)
# n_count <- letterFrequency(seq, letters = "N")[, 1]
# keep_noN <- (n_count == 0)
# filtered <- fastq[keep_noN]
# 
# if (length(filtered) == 0) {
#   stop("No reads left after filtering. All reads contain N.")
# }
# 
# # TRIM: fixed number of bases from the end, the same rule for all reads
# L <- width(sread(filtered))
# minL <- min(L)
# 
# if (TRIM_END >= minL) {
#   stop(
#     "TRIM_END is too large. Minimum read length is ",
#     minL,
#     " but TRIM_END is ",
#     TRIM_END,
#     "."
#   )
# }
# 
# endpos <- L - TRIM_END
# trimmed <- narrow(filtered, start = 1, end = endpos)
# 
# # Output names
# base <- tools::file_path_sans_ext(basename(fastqname))
# 
# out_fastq <- if (compress_out) {
#   paste0(base, "_set2_processed.fastq.gz")
# } else {
#   paste0(base, "_set2_processed.fastq")
# }
# 
# out_png <- paste0(base, "_set2_final_quality.png")
# 
# # writeFastq fails if the output already exists, so remove old file first
# if (file.exists(out_fastq)) {
#   file.remove(out_fastq)
# }
# 
# writeFastq(trimmed, out_fastq, compress = compress_out)
# 
# # Final quality boxplot after processing, saved as PNG
# qual <- as(quality(trimmed), "matrix")
# idx <- seq(1, ncol(qual), by = STEP)
# 
# png(out_png, width = 1200, height = 800, res = 150)
# 
# par(cex.axis = 0.9, cex.lab = 0.9, cex.main = 1.0)
# 
# boxplot(
#   qual[, idx, drop = FALSE],
#   xlab = "Base position",
#   ylab = "Phred quality",
#   range = 0,
#   outline = FALSE,
#   lwd = 0.3,
#   lty = 1,
#   xaxt = "n",
#   main = paste0(basename(fastqname), " - AFTER (filter N + trim ", TRIM_END, ")")
# )
# 
# axis(1, at = seq_along(idx), labels = idx)
# grid(nx = NA, ny = NULL)
# 
# invisible(dev.off())
# 
# cat("Saved processed FASTQ: ", out_fastq, "\n")
# cat("Saved final quality PNG:", out_png, "\n")
# cat("Reads total:   ", length(fastq), "\n")
# cat("Reads removed: ", sum(!keep_noN), "\n")
# cat("Reads kept:    ", length(trimmed), "\n")
# cat("Trimmed bases: ", TRIM_END, "\n")
