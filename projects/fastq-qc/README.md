# FASTQ Quality Control in R

This project presents a small bioinformatics workflow for FASTQ read quality assessment, filtering and trimming using GNU R, R Markdown and Bioconductor.

The analysis focuses on inspecting per-base Phred quality scores, identifying low-quality reads or read regions, applying filtering and trimming rules, and saving the processed FASTQ file for further analysis.

## Project goal

The goal of this project was to improve the quality of sequencing reads before downstream bioinformatics analysis.

The workflow includes:

1. loading FASTQ data,
2. extracting DNA sequences and quality scores,
3. converting encoded quality values into numeric Phred scores,
4. visualizing quality distributions,
5. filtering unreliable reads,
6. trimming low-quality read regions,
7. saving the processed FASTQ file and final quality plot.

## Tools and packages

The project was prepared using:

- R
- R Markdown
- ShortRead
- Biostrings
- knitr
- rmarkdown
- callr

## Repository structure

```text
fastq-qc/
├── index.html
├── style.css
├── README.md
├── figures/
│   ├── fastq_before.png
│   └── fastq_after.png
├── code/
│   ├── r_fastq.Rmd
│   └── fastq_filter_trim.R
└── reports/
    └── proj4_report.pdf
```

## Input data

The input data is a FASTQ file containing DNA sequencing reads and their base-level quality scores.

FASTQ files store both:

- nucleotide sequences,
- quality scores for each base.

The quality scores were analysed as numeric Phred quality values.

## Workflow overview

### 1. Load FASTQ file

```r
library(ShortRead)

fastq <- readFastq("input.fastq")
seq <- sread(fastq)
q <- quality(fastq)
```

### 2. Convert quality scores

```r
qual <- as(q, "matrix")
```

This converts encoded FASTQ quality values into a numeric Phred quality matrix.

### 3. Visualize read quality

Per-base quality distributions were visualized using boxplots.

The quality plots were generated before and after processing:

```text
figures/fastq_before.png
figures/fastq_after.png
```

### 4. Filter and trim reads

Reads were filtered based on quality criteria, and low-quality regions were trimmed.

Filtering and trimming were performed on the FASTQ object to preserve the connection between sequences, quality scores and read metadata.

### 5. Save processed data

```r
writeFastq(trimmed, "processed_reads.fastq", compress = FALSE)
```

## How to run the R Markdown file

Run all commands from the main `fastq-qc/` project folder.

### 1. Install required R packages

If the packages are not installed yet, run:

```bash
R -e "install.packages(c('rmarkdown', 'knitr', 'callr', 'BiocManager'), repos='https://cloud.r-project.org')"
```

Then install the required Bioconductor packages:

```bash
R -e "BiocManager::install(c('ShortRead', 'Biostrings'), ask = FALSE, update = FALSE)"
```

### 2. Render the R Markdown report

To render the `.Rmd` file into a PDF report, run:

```bash
Rscript -e "rmarkdown::render('code/r_fastq.Rmd', output_format = 'pdf_document', output_dir = 'reports', output_file = 'proj4_report.pdf')"
```

The generated PDF file will be saved as:

```text
reports/proj4_report.pdf
```

### 3. Alternative: render in RStudio

The report can also be generated directly in RStudio:

1. Open `code/r_fastq.Rmd`
2. Click `Knit`
3. Choose PDF output

## How to extract the standalone R script from R Markdown

The R Markdown file can be converted into a standalone `.R` script using `knitr::purl()`.

From the project folder, run:

```bash
Rscript -e "knitr::purl('code/r_fastq.Rmd', output = 'code/fastq_filter_trim.R', documentation = 0)"
```

This creates:

```text
code/fastq_filter_trim.R
```

## How to run the standalone R script

Example command:

```bash
Rscript code/fastq_filter_trim.R input.fastq
```

Depending on the script settings, the output files may include:

```text
processed_reads.fastq
final_quality_plot.pdf
```

If the script uses custom output names, run:

```bash
Rscript code/fastq_filter_trim.R input.fastq processed_reads.fastq final_quality_plot.pdf
```

## Output files

The project produces:

- a PDF report with quality plots and explanation,
- a processed FASTQ file,
- a final quality plot,
- a standalone R script extracted from the R Markdown source.

## Results

The quality of reads was compared before and after processing.

The original dataset was inspected using per-base Phred quality scores. Based on the quality profile, unreliable reads were filtered out and selected regions were trimmed. The final output contains reads with an improved quality profile.

## What I learned

This project helped me practise:

- FASTQ file handling,
- quality control of sequencing reads,
- Phred quality score interpretation,
- filtering and trimming of sequencing data,
- R scripting,
- R Markdown reporting,
- reproducible bioinformatics workflows.

## Notes

This project was prepared as a bioinformatics exercise focused on FASTQ quality control and preprocessing in R.
