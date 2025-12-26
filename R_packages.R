# IRI Study - R package installation
# Run this script to install required R packages

packages <- c(
  "tidyverse",    # Data manipulation and visualization
  "survey",       # Complex survey design analysis
  "survival",     # Survival analysis
  "tableone",     # Table 1 generation
  "broom",        # Tidy model outputs
  "knitr",        # Report generation
  "kableExtra"    # Table formatting
)

# Install missing packages
install_if_missing <- function(pkg) {
  if (!require(pkg, character.only = TRUE)) {
    install.packages(pkg, dependencies = TRUE)
    library(pkg, character.only = TRUE)
  }
}

invisible(sapply(packages, install_if_missing))

cat("All packages installed successfully!\n")

