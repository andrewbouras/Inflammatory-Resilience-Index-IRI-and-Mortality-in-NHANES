# IRI Tables Generation
# Table 1: Baseline characteristics
# Table 2: Functional outcomes by IRI

library(survey)
library(dplyr)
library(tableone)

options(survey.lonely.psu = "adjust")

# Project paths
project_root <- normalizePath(file.path(dirname(sys.frame(1)$ofile %||% "."), ".."), mustWork = FALSE)
if (!dir.exists(project_root)) {
  project_root <- normalizePath(file.path(getwd(), ".."), mustWork = FALSE)
}

# Load data
dat <- read.csv(file.path(project_root, "data", "processed", "iri_functional_cohort.csv"))

cat("Generating tables for IRI manuscript...\n\n")

# DEXA only available in 2015-2016 (single cycle); use weights directly
dat$wt_scaled <- dat$mec_weight

# Create survey design
svy <- svydesign(
  id = ~psu,
  strata = ~strata,
  weights = ~wt_scaled,
  data = dat,
  nest = TRUE
)

# ============================================================================
# TABLE 1: BASELINE CHARACTERISTICS BY IRI QUARTILE
# ============================================================================

# Variables for Table 1
vars <- c("age", "female", "race_eth", "bmi", "hscrp", "albumin", "z_almi",
          "diabetes", "hypertension", "current_smoker", "cvd_history", "cancer_history")

catVars <- c("female", "race_eth", "diabetes", "hypertension", "current_smoker", 
             "cvd_history", "cancer_history")

# Create Table 1
tab1 <- svyCreateTableOne(
  vars = vars,
  strata = "iri_quartile",
  data = svy,
  factorVars = catVars
)

# Print Table 1
cat("="," TABLE 1: BASELINE CHARACTERISTICS BY IRI QUARTILE ", "=\n\n", sep = paste(rep("=", 15), collapse = ""))

print(tab1, smd = FALSE, printToggle = FALSE) -> tab1_print
print(tab1_print)

# Save Table 1 as CSV
tab1_csv <- print(tab1, smd = FALSE, quote = FALSE, noSpaces = TRUE, printToggle = FALSE)
write.csv(tab1_csv, file.path(project_root, "output", "table1_baseline_characteristics.csv"))

cat("\nTable 1 saved to output/table1_baseline_characteristics.csv\n")

# ============================================================================
# TABLE 2: FUNCTIONAL OUTCOMES BY IRI
# ============================================================================

cat("\n\n")
cat("="," TABLE 2: FUNCTIONAL OUTCOMES BY IRI ", "=\n\n", sep = paste(rep("=", 15), collapse = ""))

# Load results dynamically from functional outcomes analysis
results_path <- file.path(project_root, "output", "functional_outcomes_results.csv")
if (file.exists(results_path)) {
  fo_results <- read.csv(results_path)
  cat("  Loaded functional outcomes results from CSV\n")
} else {
  stop("functional_outcomes_results.csv not found. Run 05_functional_analysis.R first.")
}

# Compute survey-weighted prevalence by quartile
fmt_prev <- function(outcome_var) {
  prev_vec <- c()
  for (q in c("Q1", "Q2", "Q3", "Q4")) {
    sub_svy <- subset(svy, iri_quartile == q & !is.na(dat[[outcome_var]]))
    prev <- svymean(as.formula(paste0("~", outcome_var)), sub_svy)
    prev_vec <- c(prev_vec, sprintf("%.1f%% (%.1f)", 100 * coef(prev), 100 * SE(prev)))
  }
  prev_vec
}

health_prev <- fmt_prev("poor_health")
walk_prev <- fmt_prev("difficulty_walking")
dep_prev <- fmt_prev("depression")

# Format ORs from results CSV
fmt_or <- function(row) {
  sprintf("%.2f (%.2f-%.2f)", row$OR_continuous, row$CI_low_cont, row$CI_high_cont)
}
fmt_p <- function(p) {
  if (p < 0.001) "<0.001" else sprintf("%.3f", p)
}
fmt_or_q <- function(row) {
  sprintf("%.2f (%.2f-%.2f)", row$OR_Q1vsQ4, row$CI_low_Q1, row$CI_high_Q1)
}

table2 <- data.frame(
  Outcome = c("Fair/Poor Self-Rated Health", "Difficulty Walking", "Depression (PHQ-9 >=10)"),
  Q1_prev = c(health_prev[1], walk_prev[1], dep_prev[1]),
  Q2_prev = c(health_prev[2], walk_prev[2], dep_prev[2]),
  Q3_prev = c(health_prev[3], walk_prev[3], dep_prev[3]),
  Q4_prev = c(health_prev[4], walk_prev[4], dep_prev[4]),
  OR_continuous = sapply(1:3, function(i) fmt_or(fo_results[i, ])),
  p_continuous = sapply(1:3, function(i) fmt_p(fo_results$p_continuous[i])),
  OR_Q1vsQ4 = sapply(1:3, function(i) fmt_or_q(fo_results[i, ])),
  p_Q1vsQ4 = sapply(1:3, function(i) fmt_p(fo_results$p_Q1vsQ4[i]))
)

print(table2, row.names = FALSE)

write.csv(table2, file.path(project_root, "output", "table2_functional_outcomes.csv"), row.names = FALSE)

cat("\nTable 2 saved to output/table2_functional_outcomes.csv\n")

# ============================================================================
# TABLE 3: IRI COMPONENT SUMMARY
# ============================================================================

cat("\n\n")
cat("="," TABLE 3: IRI COMPONENTS ", "=\n\n", sep = paste(rep("=", 15), collapse = ""))

# Compute Table 3 dynamically from data
t3_rows <- list()
for (q in c("Q1", "Q2", "Q3", "Q4")) {
  sub <- dat[dat$iri_quartile == q, ]
  label <- switch(q,
    "Q1" = "Q1 (Lowest Resilience)",
    "Q4" = "Q4 (Highest Resilience)",
    q
  )
  t3_rows[[q]] <- data.frame(
    Quartile = label,
    N = nrow(sub),
    IRI_mean_sd = sprintf("%.2f (%.2f)", mean(sub$iri, na.rm=TRUE), sd(sub$iri, na.rm=TRUE)),
    CRP_mean_sd = sprintf("%.2f (%.2f)", mean(sub$hscrp, na.rm=TRUE), sd(sub$hscrp, na.rm=TRUE)),
    Albumin_mean_sd = sprintf("%.2f (%.2f)", mean(sub$albumin, na.rm=TRUE), sd(sub$albumin, na.rm=TRUE)),
    ALMI_z_mean_sd = sprintf("%.2f (%.2f)", mean(sub$z_almi, na.rm=TRUE), sd(sub$z_almi, na.rm=TRUE))
  )
}
table3 <- do.call(rbind, t3_rows)

cat("Note: ALMI values are standardized z-scores, not raw kg/m² values.\n\n")
print(table3, row.names = FALSE)

write.csv(table3, file.path(project_root, "output", "table3_iri_components.csv"), row.names = FALSE)

cat("\nTable 3 saved to output/table3_iri_components.csv\n")

cat("\n\nAll tables generated successfully!\n")

